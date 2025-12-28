"""
ComfyUI Production API - Main Service Module
============================================

Core service logic only - no CLI entrypoints.
CLI functionality is handled in cli.py for clean separation.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

import modal
from modal import App, Image, Secret, Volume, asgi_app, web_server
from pydantic import BaseModel, Field

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

COMFYUI_PATH = Path("/root/comfy/ComfyUI")
MODELS_MOUNT_PATH = Path("/mnt/models")
WORKFLOWS_MOUNT_PATH = Path("/mnt/workflows")
CACHE_DIR = Path("/cache")
CONFIG_PATH = Path("/app/config")
DEFAULT_GPU = os.environ.get("DEFAULT_GPU", "L4")
COMFYUI_VERSION = os.environ.get("COMFYUI_VERSION", "0.3.41")

# ============================================================================
# LOGGING SETUP
# ============================================================================


def get_logger(name: str) -> logging.Logger:
    """Create a structured logger"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class R2OutputConfig(BaseModel):
    """Configuration for R2/S3 output storage"""

    bucket: str
    path: str = Field(default="", description="Path prefix, must end with /")
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Request model for workflow execution"""

    workflow_id: str = Field(description="Name of workflow file without .json")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to inject: {'node_id.input_name': value} or {'input_name': value}",
    )
    output: Optional[R2OutputConfig] = Field(
        default=None, description="Optional R2/S3 output configuration"
    )
    client_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class GenerationStatus(BaseModel):
    """Status update model for real-time progress"""

    status: str  # starting, queued, running, completed, error
    prompt_id: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_node: Optional[str] = None
    error: Optional[str] = None
    result_type: Optional[str] = None  # base64, url
    result_data: Optional[str] = None
    filename: Optional[str] = None


# ============================================================================
# MODAL APP SETUP
# ============================================================================

app = App("comfyui-production-api")

# Create persistent volumes
model_volume = Volume.from_name("comfyui-models", create_if_missing=True)
workflow_volume = Volume.from_name("comfyui-workflows", create_if_missing=True)
cache_volume = Volume.from_name("hf-hub-cache", create_if_missing=True)

# Create secret for environment variables
secret = Secret.from_dotenv()

# ============================================================================
# IMAGE DEFINITION (Minimal Build)
# ============================================================================


def install_comfyui():
    """Install ComfyUI during image build with better error handling"""
    print("🔧 Installing ComfyUI...")
    
    # Create target directory
    COMFYUI_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Method 1: Use comfy-cli
    cmd = f"comfy --skip-prompt install --nvidia --version {COMFYUI_VERSION}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=COMFYUI_PATH.parent)
    
    if result.returncode == 0:
        print(f"✅ ComfyUI {COMFYUI_VERSION} installed successfully via comfy-cli")
    else:
        print(f"❌ comfy-cli installation failed: {result.stderr}")
        print("🔄 Trying manual installation...")
        # Method 2: Manual git clone as fallback
        try:
            # Clone ComfyUI
            clone_cmd = f"git clone https://github.com/comfyanonymous/ComfyUI.git {COMFYUI_PATH}"
            result = subprocess.run(clone_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            # Install requirements
            req_cmd = f"pip install -r {COMFYUI_PATH / 'requirements.txt'}"
            result = subprocess.run(req_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Requirements install failed: {result.stderr}")
                
            print("✅ ComfyUI installed successfully via git clone")
            
        except Exception as e:
            raise Exception(f"Both installation methods failed: {e}")
    
    # Verify installation
    # try:
    #     import sys
    #     sys.path.insert(0, str(COMFYUI_PATH))
    #     import comfy.options
    #     print("✅ ComfyUI modules verified")
    #
    # except ImportError as e:
    #     print(f"⚠️ ComfyUI installed but import failed: {e}")
    #     print("This might be a path issue that will resolve at runtime")
    
    print(f"📁 ComfyUI installed at: {COMFYUI_PATH}")

# Minimal image with only core dependencies
image = (
    Image.debian_slim(python_version="3.11")
    .apt_install(
        "git",
        "wget",
        "curl",
        "aria2",
        "libgl1-mesa-glx",
        "libglib2.0-0",  # Required for some custom nodes
    )
    .pip_install(
        [
            "comfy-cli==1.3.7",
            "websockets==12.0",
            "requests==2.31.0",
            "python-dotenv==1.0.1",
            "huggingface_hub[hf_transfer]==0.29.2",
            "boto3==1.37.7",
            "pyyaml==6.0.1",
            "fastapi[standard]==0.115.4",
            "pydantic==2.5.0",
            "aiofiles==23.2.1",
        ]
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_HUB_CACHE": str(CACHE_DIR),
            "PYTHONUNBUFFERED": "1",
        }
    )
    .run_function(install_comfyui, secrets=[secret])
    .add_local_dir("comfy_service/config", str(CONFIG_PATH))  # Add config files
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _download_single_model(model_info: dict, models_dir: Path, logger: logging.Logger):
    """Download a single model based on configuration"""
    model_type = model_info.get("type", "checkpoints")
    source = model_info.get("source", "huggingface")

    # Create target directory
    target_dir = models_dir / model_type
    target_dir.mkdir(parents=True, exist_ok=True)

    if source == "huggingface":
        from huggingface_hub import hf_hub_download

        repo_id = model_info["repo_id"]
        filename = model_info["filename"]

        save_as = model_info.get("save_as", filename)

        logger.info(f"Downloading {repo_id}/{filename}...")

        try:
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=str(CACHE_DIR),
                resume_download=True,
            )

            # Create symlink in ComfyUI models directory
            target_path = target_dir / save_as
            if not target_path.exists():
                target_path.symlink_to(downloaded_path)
                logger.info(f"✅ Linked {save_as} to {target_path}")
            else:
                logger.info(f"ℹ️ {save_as} already exists")

        except Exception as e:
            logger.error(f"❌ Failed to download {repo_id}/{filename}: {e}")

            raise

    elif source == "civitai":
        # Handle both direct URL and model_id approaches
        if "url" in model_info:
            # Direct URL download
            url = model_info["url"]
            save_as = model_info.get("save_as", url.split("/")[-1].split("?")[0])
            target_path = target_dir / save_as

            if target_path.exists():
                logger.info(f"ℹ️ {save_as} already exists, skipping")
                return

            logger.info(f"Downloading {save_as} from Civitai URL...")
            _download_from_url(url, target_path, logger)

        elif "model_id" in model_info:
            # API-based download
            import requests

            model_id = model_info["model_id"]
            version_id = model_info.get("version_id")
            api_key = os.environ.get("CIVITAI_API_KEY", "")
            save_as = model_info.get("save_as")

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            logger.info(f"Fetching model info for Civitai model {model_id}...")

            # Get model info from Civitai API

            response = requests.get(
                f"https://civitai.com/api/v1/models/{model_id}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            model_data = response.json()

            # Find the right version
            if version_id:
                version = next(
                    (v for v in model_data["modelVersions"] if v["id"] == version_id),
                    None,
                )
                if not version:
                    raise ValueError(
                        f"Version {version_id} not found for model {model_id}"
                    )
            else:
                version = model_data["modelVersions"][0]  # Latest version

            # Get the primary file

            file_info = version["files"][0]
            download_url = file_info["downloadUrl"]
            filename = save_as or file_info["name"]
            target_path = target_dir / filename

            if target_path.exists():

                logger.info(f"ℹ️ {filename} already exists, skipping")
                return

            logger.info(f"Downloading {filename} from Civitai...")
            _download_from_url(download_url, target_path, logger, headers)

        else:

            raise ValueError("Civitai models require either 'url' or 'model_id'")

    elif source == "url":
        # Generic URL download
        url = model_info["url"]
        save_as = model_info.get("save_as", url.split("/")[-1].split("?")[0])
        target_path = target_dir / save_as

        if target_path.exists():
            logger.info(f"ℹ️ {save_as} already exists, skipping")
            return

        logger.info(f"Downloading {save_as} from URL...")
        _download_from_url(url, target_path, logger)

    elif source == "s3":
        # S3/R2 download
        import boto3

        bucket = model_info["bucket"]
        key = model_info["key"]
        save_as = model_info.get("save_as", key.split("/")[-1])

        target_path = target_dir / save_as

        if target_path.exists():
            logger.info(f"ℹ️ {save_as} already exists, skipping")
            return

        logger.info(f"Downloading {save_as} from S3...")

        try:
            # Configure S3 client
            s3_client = boto3.client(
                "s3",
                endpoint_url=model_info.get("endpoint_url"),
                aws_access_key_id=model_info.get("access_key_id")
                or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=model_info.get("secret_access_key")
                or os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=model_info.get("region", "auto"),
            )

            # Download file
            s3_client.download_file(bucket, key, str(target_path))
            logger.info(f"✅ Downloaded {save_as} from S3")

        except Exception as e:
            logger.error(f"❌ Failed to download s3://{bucket}/{key}: {e}")
            if target_path.exists():
                target_path.unlink()  # Clean up partial download
            raise

    else:
        raise ValueError(f"Unsupported source: {source}")


def _download_from_url(
    url: str, target_path: Path, logger: logging.Logger, headers: dict = None
):
    """Helper function to download from URL with progress tracking"""
    import requests

    if headers is None:
        headers = {}

    try:
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Log progress every 50MB
                    if total_size > 0 and downloaded % (50 * 1024 * 1024) == 0:
                        progress = downloaded / total_size * 100
                        logger.info(
                            f"Progress: {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB)"
                        )

        logger.info(f"✅ Downloaded {target_path.name}")

    except Exception as e:
        logger.error(f"❌ Failed to download {url}: {e}")
        if target_path.exists():
            target_path.unlink()  # Clean up partial download

        raise


# ============================================================================
# CORE COMFYUI SERVICE
# ============================================================================


@app.cls(
    gpu=DEFAULT_GPU,
    image=image,
    volumes={
        str(MODELS_MOUNT_PATH): model_volume,
        str(WORKFLOWS_MOUNT_PATH): workflow_volume,
        str(CACHE_DIR): cache_volume,
    },
    secrets=[secret],
    scaledown_window=600,  # 10 minutes
    enable_memory_snapshot=True,
)
class ComfyUIService:
    """Production-ready ComfyUI service with WebSocket API"""

    @modal.enter(snap=True)
    def setup_pre_snapshot(self):
        """Pre-snapshot setup: Install custom nodes (cached)"""
        self.logger = get_logger(self.__class__.__name__)
        self.server_address = "127.0.0.1:8188"
        self.server_process = None
        self.logger.info("🔧 PRE-SNAPSHOT: Installing custom nodes...")

        # Create symlink for models directory
        if not COMFYUI_PATH.joinpath("models").exists():
            COMFYUI_PATH.joinpath("models").symlink_to(MODELS_MOUNT_PATH)
            self.logger.info("📁 Created models symlink")

        # Install custom nodes with improved system
        install_result = self.install_custom_nodes()

        if install_result["status"] == "completed":
            self.logger.info("🎉 All custom nodes installed successfully!")
        elif install_result["status"] == "partial":
            self.logger.warning(
                f"⚠️ Partial installation: {install_result['summary']['failed']} nodes failed"
            )
        elif install_result["status"] == "error":
            self.logger.error(
                f"❌ Custom node installation error: {install_result['message']}"
            )
        else:
            self.logger.info("ℹ️ Custom node installation skipped")

        self.logger.info("✅ PRE-SNAPSHOT COMPLETE")

    @modal.enter(snap=False)
    def setup_post_snapshot(self):
        """Post-snapshot setup: Start ComfyUI server (fast)"""
        self.logger.info("🚀 POST-SNAPSHOT: Starting ComfyUI server...")

        # Start ComfyUI server in background
        cmd = [
            "python",
            str(COMFYUI_PATH / "main.py"),
            "--listen",
            self.server_address.split(":")[0],
            "--port",
            self.server_address.split(":")[1],
            "--disable-auto-launch",
            "--disable-metadata",
        ]

        self.server_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Wait for server to be ready
        self._wait_for_server()
        self.logger.info("✅ ComfyUI server ready")

    @modal.exit()
    def cleanup(self):
        """Graceful shutdown"""
        self.logger.info("🛑 Shutting down ComfyUI server...")
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        self.logger.info("✅ Server shut down")

    def install_custom_nodes(self):
        """Install custom nodes from config with improved error handling and priority support"""
        self.logger.info("🔧 Installing custom nodes...")

        config_path = CONFIG_PATH / "custom_nodes.json"
        if not config_path.exists():
            self.logger.info(
                "ℹ️ No custom_nodes.json found, skipping custom node installation"
            )
            return {"status": "skipped", "message": "No config file found"}

        try:
            with open(config_path) as f:
                nodes = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON in custom_nodes.json: {e}")
            return {"status": "error", "message": f"Invalid JSON: {e}"}

        if not isinstance(nodes, list):
            self.logger.error("❌ custom_nodes.json must contain a list of nodes")
            return {"status": "error", "message": "Config must be a list"}

        # Sort nodes by priority (critical -> high -> medium -> low)

        priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}

        nodes_sorted = sorted(
            nodes, key=lambda x: priority_order.get(x.get("priority", "medium"), 3)
        )

        self.logger.info(f"📦 Found {len(nodes_sorted)} custom nodes to install")

        # Track installation results
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total": len(nodes_sorted),
        }

        for i, node in enumerate(nodes_sorted, 1):

            if not isinstance(node, dict) or "name" not in node:
                self.logger.warning(f"⚠️ Invalid node configuration: {node}")
                results["skipped"].append(
                    {"name": "unknown", "reason": "Invalid config"}
                )
                continue

            node_name = node["name"]
            priority = node.get("priority", "medium")
            category = node.get("category", "unknown")

            self.logger.info(
                f"[{i}/{len(nodes_sorted)}] Installing {node_name} ({priority} priority, {category})"
            )

            try:
                # Use comfy node install command
                cmd = f"comfy node install {node_name}"

                # Set timeout based on priority
                timeout = {
                    "critical": 600,  # 10 minutes for critical nodes
                    "high": 480,  # 8 minutes for high priority
                    "medium": 300,  # 5 minutes for medium priority
                    "low": 240,  # 4 minutes for low priority
                }.get(priority, 300)

                result = subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                results["successful"].append(
                    {"name": node_name, "priority": priority, "category": category}
                )
                self.logger.info(f"✅ Successfully installed {node_name}")

            except subprocess.TimeoutExpired:
                error_msg = f"Installation timeout after {timeout}s"
                results["failed"].append(
                    {"name": node_name, "priority": priority, "error": error_msg}
                )
                self.logger.error(f"⏰ {error_msg} for {node_name}")

            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"Installation failed: {e.stderr or e.stdout or 'Unknown error'}"
                )
                results["failed"].append(
                    {"name": node_name, "priority": priority, "error": error_msg}
                )
                self.logger.error(f"❌ Failed to install {node_name}: {error_msg}")

                # For critical nodes, log more details
                if priority == "critical":
                    self.logger.error(
                        f"🚨 CRITICAL NODE FAILED: {node_name} - This may affect core functionality"
                    )

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                results["failed"].append(
                    {"name": node_name, "priority": priority, "error": error_msg}
                )
                self.logger.error(
                    f"❌ Unexpected error installing {node_name}: {error_msg}"
                )

        # Summary
        successful_count = len(results["successful"])
        failed_count = len(results["failed"])
        skipped_count = len(results["skipped"])

        self.logger.info(f"🎯 Custom node installation complete:")
        self.logger.info(f"   ✅ Successful: {successful_count}")
        self.logger.info(f"   ❌ Failed: {failed_count}")
        self.logger.info(f"   ⏭️ Skipped: {skipped_count}")

        # Log failed critical/high priority nodes
        critical_failed = [
            n for n in results["failed"] if n.get("priority") in ["critical", "high"]
        ]
        if critical_failed:
            self.logger.warning(
                f"⚠️ {len(critical_failed)} critical/high priority nodes failed:"
            )
            for node in critical_failed:
                self.logger.warning(f"   - {node['name']}: {node['error']}")

        return {
            "status": "completed" if failed_count == 0 else "partial",
            "results": results,
            "summary": {
                "successful": successful_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": len(nodes_sorted),
            },
        }

    def _wait_for_server(self, timeout: int = 60):
        """Wait for ComfyUI server to become responsive"""
        import requests

        start_time = time.time()
        server_url = f"http://{self.server_address}"

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{server_url}/system_stats", timeout=5)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)

        raise RuntimeError("ComfyUI server failed to start within timeout")

    async def _execute_workflow_with_streaming(
        self, websocket, request: WorkflowRequest
    ):
        """Execute workflow with real-time progress streaming"""
        import websockets
        import requests

        try:
            # Send initial status
            await websocket.send_json(
                GenerationStatus(
                    status="starting", message="Loading workflow..."
                ).model_dump()
            )

            # Load workflow
            workflow_path = WORKFLOWS_MOUNT_PATH / f"{request.workflow_id}.json"
            if not workflow_path.exists():
                raise FileNotFoundError(
                    f"Workflow '{request.workflow_id}.json' not found"
                )

            with open(workflow_path) as f:
                workflow = json.load(f)

            # Apply parameters
            if request.params:
                self._apply_parameters(workflow, request.params)

            await websocket.send_json(
                GenerationStatus(
                    status="queued", message="Connecting to ComfyUI server..."
                ).model_dump()
            )

            # Connect to ComfyUI WebSocket
            ws_url = f"ws://{self.server_address}/ws?clientId={request.client_id}"
            async with websockets.connect(ws_url, timeout=10) as comfy_ws:

                # Queue the workflow
                prompt_data = {"prompt": workflow, "client_id": request.client_id}
                response = await asyncio.to_thread(
                    requests.post,
                    f"http://{self.server_address}/prompt",
                    json=prompt_data,
                    timeout=30,
                )
                response.raise_for_status()
                prompt_id = response.json()["prompt_id"]

                await websocket.send_json(
                    GenerationStatus(
                        status="running",
                        prompt_id=prompt_id,
                        message="Workflow execution started",
                    ).model_dump()
                )

                # Track progress
                output_images = []
                while True:
                    try:
                        message_str = await asyncio.wait_for(
                            comfy_ws.recv(), timeout=300
                        )
                        message = json.loads(message_str)

                        # Parse ComfyUI messages and send progress updates
                        status_update = self._parse_comfy_message(message, prompt_id)
                        if status_update:
                            await websocket.send_json(status_update.model_dump())

                        # Check for completion
                        if (
                            message["type"] == "executing"
                            and message["data"]["node"] is None
                            and message["data"]["prompt_id"] == prompt_id
                        ):
                            break

                        # Collect output images
                        if (
                            message["type"] == "executed"
                            and "output" in message["data"]
                        ):
                            node_output = message["data"]["output"]
                            if "images" in node_output:
                                output_images.extend(node_output["images"])

                    except asyncio.TimeoutError:
                        raise Exception("Workflow execution timed out after 5 minutes")

            # Process and send results
            await self._send_results(websocket, output_images, request, prompt_id)

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            await websocket.send_json(
                GenerationStatus(status="error", error=str(e)).model_dump()
            )

    def _apply_parameters(self, workflow: dict, params: dict):
        """Apply parameters to workflow nodes"""
        for param_key, param_value in params.items():
            if "." in param_key:
                # Format: "node_id.input_name"
                node_id, input_name = param_key.split(".", 1)
                if node_id in workflow and "inputs" in workflow[node_id]:
                    if input_name in workflow[node_id]["inputs"]:
                        workflow[node_id]["inputs"][input_name] = param_value
            else:
                # Search all nodes for matching input name
                for node_id, node in workflow.items():
                    if "inputs" in node and param_key in node["inputs"]:
                        node["inputs"][param_key] = param_value
                        break

    def _parse_comfy_message(
        self, message: dict, prompt_id: str
    ) -> Optional[GenerationStatus]:
        """Parse ComfyUI WebSocket messages into status updates"""
        msg_type = message.get("type")
        data = message.get("data", {})

        if msg_type == "progress":
            # K-sampler progress
            current = data.get("value", 0)
            total = data.get("max", 1)
            progress = current / total if total > 0 else 0

            return GenerationStatus(
                status="running",
                prompt_id=prompt_id,
                progress=progress,
                current_step=current,
                total_steps=total,
                message=f"Sampling: {current}/{total}",
            )

        elif msg_type == "executing":
            # Node execution
            node = data.get("node")
            if node:
                return GenerationStatus(
                    status="running",
                    prompt_id=prompt_id,
                    current_node=node,
                    message=f"Executing node: {node}",
                )

        elif msg_type == "execution_error":
            # Execution error
            return GenerationStatus(
                status="error", prompt_id=prompt_id, error=str(data)
            )

        return None

    async def _send_results(
        self,
        websocket,
        output_images: List[dict],
        request: WorkflowRequest,
        prompt_id: str,
    ):
        """Send final results to client"""
        if request.output and request.output.bucket:
            # Upload to R2/S3
            await self._upload_to_storage(websocket, output_images, request.output)
        else:
            # Send as base64
            await self._send_images_as_base64(websocket, output_images)

        # Send completion status
        await websocket.send_json(
            GenerationStatus(
                status="completed",
                prompt_id=prompt_id,
                message=f"Generated {len(output_images)} images successfully",
            ).model_dump()
        )

    async def _send_images_as_base64(self, websocket, output_images: List[dict]):
        """Send images as base64 encoded data"""
        import requests

        for img in output_images:
            try:
                image_url = f"http://{self.server_address}/view"
                params = {
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                }

                response = await asyncio.to_thread(
                    requests.get, image_url, params=params, timeout=30
                )
                response.raise_for_status()

                encoded = base64.b64encode(response.content).decode("utf-8")
                await websocket.send_json(
                    GenerationStatus(
                        status="result",
                        result_type="base64",
                        result_data=encoded,
                        filename=img["filename"],
                    ).model_dump()
                )

            except Exception as e:
                self.logger.error(f"Failed to send image {img['filename']}: {e}")

    async def _upload_to_storage(
        self, websocket, output_images: List[dict], output_config: R2OutputConfig
    ):
        """Upload images to R2/S3 storage"""
        import boto3
        import requests

        try:
            # Configure S3/R2 client
            s3_client = boto3.client(
                "s3",
                endpoint_url=output_config.endpoint_url,
                aws_access_key_id=output_config.access_key_id
                or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=output_config.secret_access_key
                or os.environ.get("AWS_SECRET_ACCESS_KEY"),
            )

            for img in output_images:
                try:
                    # Download image from ComfyUI
                    image_url = f"http://{self.server_address}/view"
                    params = {
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                    }

                    response = await asyncio.to_thread(
                        requests.get, image_url, params=params, timeout=30
                    )
                    response.raise_for_status()

                    # Upload to storage
                    key = f"{output_config.path}{img['filename']}"
                    await asyncio.to_thread(
                        s3_client.put_object,
                        Bucket=output_config.bucket,
                        Key=key,
                        Body=response.content,
                        ContentType="image/png",
                    )

                    # Send URL to client
                    url = f"s3://{output_config.bucket}/{key}"
                    await websocket.send_json(
                        GenerationStatus(
                            status="result",
                            result_type="url",
                            result_data=url,
                            filename=img["filename"],
                        ).model_dump()
                    )

                except Exception as e:
                    self.logger.error(f"Failed to upload {img['filename']}: {e}")

        except Exception as e:
            self.logger.error(f"Storage upload failed: {e}")
            await websocket.send_json(
                GenerationStatus(
                    status="error", error=f"Storage upload failed: {e}"
                ).model_dump()
            )

    @modal.method()
    async def execute_workflow_streaming(self, request: WorkflowRequest):
        """Execute workflow with streaming (for testing without WebSocket)"""
        # This is a simplified version for direct method calls
        workflow_path = WORKFLOWS_MOUNT_PATH / f"{request.workflow_id}.json"
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow '{request.workflow_id}.json' not found")

        with open(workflow_path) as f:
            workflow = json.load(f)

        if request.params:
            self._apply_parameters(workflow, request.params)

        # Simple execution without streaming
        import requests

        prompt_data = {"prompt": workflow, "client_id": request.client_id}
        response = requests.post(
            f"http://{self.server_address}/prompt", json=prompt_data
        )
        response.raise_for_status()

        return {"status": "queued", "prompt_id": response.json()["prompt_id"]}


# ============================================================================
# MANAGEMENT FUNCTIONS
# ============================================================================


@app.function(
    image=image,
    volumes={str(MODELS_MOUNT_PATH): model_volume},
    secrets=[secret],
    timeout=7200,  # 2 hours for large downloads
)
def download_models():
    """Download all models from config to persistent volume"""
    logger = get_logger("model_downloader")
    config_path = CONFIG_PATH / "models.yaml"

    if not config_path.exists():
        logger.error("❌ models.yaml not found in config directory")
        return {"status": "error", "message": "models.yaml not found"}

    with open(config_path) as f:
        models = yaml.safe_load(f)

    logger.info(f"📥 Found {len(models)} models to download")

    successful = 0
    failed = 0
    errors = []

    for model_id, model_info in models.items():
        try:
            logger.info(f"📦 Downloading model: {model_id}")
            _download_single_model(model_info, MODELS_MOUNT_PATH, logger)
            successful += 1
        except Exception as e:
            logger.error(f"❌ Failed to download {model_id}: {e}")
            errors.append(f"{model_id}: {str(e)}")
            failed += 1

    # Commit changes to volume
    logger.info("💾 Committing changes to model volume...")
    model_volume.commit()

    result = {
        "status": "completed" if failed == 0 else "partial",
        "successful": successful,
        "failed": failed,
        "total": len(models),
        "errors": errors if errors else None,
    }

    logger.info(f"✅ Model download complete: {successful}/{len(models)} successful")
    return result


@app.function(
    image=image,
    volumes={str(WORKFLOWS_MOUNT_PATH): workflow_volume},
)
def sync_workflows():
    """Sync local workflows directory to persistent volume"""
    logger = get_logger("workflow_syncer")
    source_dir = Path("comfy_service/workflows")
    dest_dir = WORKFLOWS_MOUNT_PATH

    if not source_dir.exists():
        logger.warning("⚠️ Local 'workflows' directory not found")
        return {"status": "error", "message": "Local workflows directory not found"}

    logger.info(f"🔄 Syncing workflows from {source_dir} to {dest_dir}")

    # Copy all .json files
    workflow_files = list(source_dir.glob("*.json"))
    if not workflow_files:
        logger.warning("⚠️ No .json workflow files found")
        return {"status": "warning", "message": "No workflow files found"}

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    synced = 0
    for workflow_file in workflow_files:
        try:
            dest_file = dest_dir / workflow_file.name
            shutil.copy2(workflow_file, dest_file)
            logger.info(f"📄 Synced: {workflow_file.name}")
            synced += 1
        except Exception as e:
            logger.error(f"❌ Failed to sync {workflow_file.name}: {e}")

    # Commit changes
    workflow_volume.commit()

    result = {"status": "completed", "synced": synced, "total": len(workflow_files)}

    logger.info(f"✅ Workflow sync complete: {synced}/{len(workflow_files)} files")
    return result


@app.function(image=image, secrets=[secret])
def create_config_templates():
    """Create example configuration files"""
    from pathlib import Path

    logger = get_logger("config_creator")
    logger.info("📝 Creating configuration templates...")

    # Create directories
    config_dir = Path("/tmp/config")
    workflows_dir = Path("/tmp/workflows")
    config_dir.mkdir(exist_ok=True)
    workflows_dir.mkdir(exist_ok=True)

    # Create models.yaml template
    models_config = {
        "flux-schnell": {
            "type": "checkpoints",
            "source": "huggingface",
            "repo_id": "Comfy-Org/flux1-schnell",
            "filename": "flux1-schnell-fp8.safetensors",
        },
        "realistic-vision": {
            "type": "checkpoints",
            "source": "civitai",
            "model_id": "4201",
        },
        "controlnet-canny": {
            "type": "controlnet",
            "source": "huggingface",
            "repo_id": "lllyasviel/sd-controlnet-canny",
            "filename": "diffusion_pytorch_model.safetensors",
        },
    }

    with open(config_dir / "models.yaml", "w") as f:
        yaml.dump(models_config, f, default_flow_style=False)

    # Create custom_nodes.json template
    custom_nodes = [
        {
            "name": "was-node-suite-comfyui",
            "description": "WAS Node Suite - Essential image processing",
        },
        {"name": "ComfyUI-Manager", "description": "Node manager for ComfyUI"},
        {
            "name": "ComfyUI-Impact-Pack",
            "description": "Face enhancement and segmentation",
        },
    ]

    with open(config_dir / "custom_nodes.json", "w") as f:
        json.dump(custom_nodes, f, indent=2)

    # Create example workflow
    example_workflow = {
        "3": {
            "inputs": {
                "seed": 123456,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "4": {
            "inputs": {"ckpt_name": "flux1-schnell-fp8.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "5": {
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "6": {
            "inputs": {"text": "a beautiful landscape", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "7": {
            "inputs": {"text": "blurry, low quality", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            "class_type": "VAEDecode",
        },
        "9": {
            "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
            "class_type": "SaveImage",
        },
    }

    with open(workflows_dir / "txt2img.json", "w") as f:
        json.dump(example_workflow, f, indent=2)

    logger.info("✅ Configuration templates created")
    return {
        "status": "success",
        "message": "Templates created successfully",
        "files": [
            "config/models.yaml",
            "config/custom_nodes.json",
            "workflows/txt2img.json",
        ],
    }


@app.function(image=image, secrets=[secret])
def test_websocket(
    workflow_id: str = "txt2img",
    prompt: str = "a beautiful sunset over mountains",
    steps: int = 20,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
):
    """Test WebSocket API functionality"""
    import asyncio
    import websockets
    import json

    logger = get_logger("websocket_tester")
    logger.info(f"🧪 Testing WebSocket API with workflow: {workflow_id}")

    async def test():
        api_url = api.web_url
        ws_url = api_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url += "/api/v1/generate"

        logger.info(f"🔗 Connecting to: {ws_url}")

        request_data = {
            "workflow_id": workflow_id,
            "params": {
                "text": prompt,
                "6.text": prompt,  # Common text input node
                "steps": steps,
                "cfg": cfg,
                "width": width,
                "height": height,
            },
        }

        try:
            async with websockets.connect(ws_url) as websocket:
                # Send request
                await websocket.send(json.dumps(request_data))
                logger.info("📤 Request sent")

                # Receive updates
                results = []
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    status = data.get("status")

                    if status == "starting":
                        logger.info("🚀 Starting generation...")
                    elif status == "queued":
                        logger.info("⏳ Queued for execution")
                    elif status == "running":
                        progress = data.get("progress")
                        if progress is not None:
                            logger.info(f"🎨 Progress: {progress:.1%}")
                        current_node = data.get("current_node")
                        if current_node:
                            logger.info(f"🔧 Executing: {current_node}")
                    elif status == "result":
                        logger.info(f"📸 Result: {data.get('filename')}")
                        results.append(data.get("filename"))
                    elif status == "completed":
                        logger.info("✅ Generation completed!")
                        break
                    elif status == "error":
                        logger.error(f"❌ Error: {data.get('error')}")
                        return {"status": "error", "error": data.get("error")}

                return {
                    "status": "success",
                    "results": results,
                    "message": f"Generated {len(results)} images",
                }

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"status": "error", "error": str(e)}

    return asyncio.run(test())


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.function(
    gpu=DEFAULT_GPU,
    image=image,
    volumes={
        str(MODELS_MOUNT_PATH): model_volume,
        str(WORKFLOWS_MOUNT_PATH): workflow_volume,
        str(CACHE_DIR): cache_volume,
    },
    secrets=[secret],
    scaledown_window=600,
    enable_memory_snapshot=True,
)
@asgi_app()
def api():
    """Production FastAPI app with WebSocket support"""
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(
        title="ComfyUI Production API",
        description="Production-ready ComfyUI API with WebSocket streaming",
        version="1.0.0",
    )

    # Add CORS middleware
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create ComfyUI service instance
    comfy_service = ComfyUIService()
    logger = get_logger("api")

    @web_app.websocket("/api/v1/generate")
    async def generate_websocket(websocket: WebSocket):
        """WebSocket endpoint for real-time workflow execution"""
        await websocket.accept()
        try:
            # Receive request
            request_data = await websocket.receive_json()
            request = WorkflowRequest(**request_data)

            logger.info(f"🎨 Starting workflow: {request.workflow_id}")

            # Execute workflow with streaming
            await comfy_service._execute_workflow_with_streaming(websocket, request)

        except WebSocketDisconnect:
            logger.info("👋 Client disconnected")
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}", exc_info=True)
            try:
                await websocket.send_json(
                    GenerationStatus(status="error", error=str(e)).model_dump()
                )
            except Exception:
                pass  # Connection might be closed

    @web_app.post("/api/v1/generate", response_model=dict)
    async def generate_simple(request: WorkflowRequest):
        """Simple REST endpoint for workflow execution (no streaming)"""
        try:
            result = await comfy_service.execute_workflow_streaming.aio(request)
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @web_app.get("/api/v1/workflows", response_model=List[str])
    async def list_workflows():
        """List available workflows"""
        try:
            workflow_files = list(WORKFLOWS_MOUNT_PATH.glob("*.json"))
            workflows = [f.stem for f in workflow_files]
            return JSONResponse({"workflows": workflows})
        except Exception as e:
            logger.error(f"❌ Failed to list workflows: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @web_app.get("/api/v1/models", response_model=dict)
    async def list_models():
        """List available models by type"""
        try:
            models = {}
            for model_type_dir in MODELS_MOUNT_PATH.iterdir():
                if model_type_dir.is_dir():
                    model_files = [
                        f.name for f in model_type_dir.glob("*") if f.is_file()
                    ]
                    models[model_type_dir.name] = model_files
            return JSONResponse({"models": models})
        except Exception as e:
            logger.error(f"❌ Failed to list models: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @web_app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return JSONResponse(
            {
                "status": "healthy",
                "service": "comfyui-production-api",
                "version": "1.0.0",
            }
        )

    @web_app.get("/")
    async def root():
        """Root endpoint with API information"""
        return JSONResponse(
            {
                "message": "ComfyUI Production API",
                "endpoints": {
                    "websocket": "/api/v1/generate",
                    "rest": "/api/v1/generate",
                    "workflows": "/api/v1/workflows",
                    "models": "/api/v1/models",
                    "health": "/health",
                },
                "docs": "/docs",
            }
        )

    return web_app


# ============================================================================
# DEVELOPMENT UI
# ============================================================================


@app.function(
    gpu=DEFAULT_GPU,
    image=image,
    volumes={
        str(MODELS_MOUNT_PATH): model_volume,
        str(WORKFLOWS_MOUNT_PATH): workflow_volume,
        str(CACHE_DIR): cache_volume,
    },
    secrets=[secret],
    scaledown_window=1200,  # 20 minutes for development
)
@web_server(8000, startup_timeout=180)
def ui():
    """Interactive ComfyUI for development and workflow creation"""
    logger = get_logger("comfyui_ui")
    logger.info("🎨 Starting ComfyUI development interface...")

    # Create models symlink if needed
    if not COMFYUI_PATH.joinpath("models").exists():
        COMFYUI_PATH.joinpath("models").symlink_to(MODELS_MOUNT_PATH)

    # Start ComfyUI with web interface
    cmd = "comfy launch -- --listen 0.0.0.0 --port 8000"
    subprocess.Popen(cmd, shell=True)
