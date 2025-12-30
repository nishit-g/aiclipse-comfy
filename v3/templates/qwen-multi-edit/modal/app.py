"""
AiClipse ComfyUI - Qwen Multi-Edit Template
Modal Deployment

Deploy: modal deploy v3/templates/qwen-multi-edit/modal/app.py
Serve:  modal serve v3/templates/qwen-multi-edit/modal/app.py
"""

import os
import sys
from pathlib import Path

import modal

# Add shared library to path
TEMPLATE_DIR = Path(__file__).parent.parent
V3_DIR = TEMPLATE_DIR.parent.parent
sys.path.insert(0, str(V3_DIR / "shared"))

from aiclipse import Config, ModelDownloader, ComfyLauncher, setup_model_paths
from aiclipse.gpu import get_gpu_config, GPUVariant

# =============================================================================
# Configuration
# =============================================================================
TEMPLATE_NAME = "qwen-multi-edit"
CONFIG_PATH = TEMPLATE_DIR / "config.yaml"

# GPU Variants - create separate apps for different GPUs
GPU_VARIANT = os.environ.get("GPU_VARIANT", "a10g")
GPU = get_gpu_config(GPU_VARIANT)

# Volume names (v2 volumes for better performance)
# v2 benefits: unlimited files, hundreds of concurrent writers, faster commits/reloads
MODELS_VOLUME_NAME = "aiclipse-models-v2"
OUTPUTS_VOLUME_NAME = "aiclipse-outputs-v2"

# Paths inside container
MODELS_PATH = "/models"
OUTPUTS_PATH = "/outputs"
COMFY_PATH = "/root/comfy"  # comfy-cli workspace
COMFY_UI_PATH = "/root/comfy/ComfyUI"  # actual ComfyUI installation (where main.py is)

# =============================================================================
# Modal App
# =============================================================================

# Try to load secrets (optional for serving, required for downloads)
app_secrets = []
try:
    app_secrets.append(modal.Secret.from_name("huggingface-secret"))
except:
    pass
try:
    app_secrets.append(modal.Secret.from_name("r2-secret"))
except:
    pass

app = modal.App(name=f"comfy-{TEMPLATE_NAME}")

# Volumes
models_volume = modal.Volume.from_name(MODELS_VOLUME_NAME, create_if_missing=True)
outputs_volume = modal.Volume.from_name(OUTPUTS_VOLUME_NAME, create_if_missing=True)

# =============================================================================
# Docker Image (Optimized Layering)
# =============================================================================
# 
# Layer Strategy:
# 1. base_image: System deps + Python packages (rarely changes, cached long)
# 2. download_image: Adds aria2c for fast downloads (used by download_models)
# 3. comfy_image: ComfyUI installation (changes on ComfyUI version bump)
# 4. template_image: Template files (changes often, small layer)
#
# This ordering ensures maximum cache reuse.

# Layer 1: Base Python + system deps (CACHED LONG TERM)
base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        # Core tools
        "git", "git-lfs", "wget", "curl",
        # Video/Image processing
        "ffmpeg", "libgl1", "libglib2.0-0",
        # Debug tools
        "htop", "nano",
    )
    .pip_install(
        # ComfyUI CLI
        "comfy-cli>=1.0.0",
        # Model downloads
        "huggingface-hub",
        "boto3",
        # Config
        "pyyaml",
        "safetensors",
        # API
        "fastapi[standard]",
    )
)

# Layer 2: Download tools (for download_models function)
download_image = (
    base_image
    .apt_install("aria2")  # Fast parallel downloader
    .add_local_dir(str(V3_DIR / "shared"), "/app/shared", copy=True)
    .add_local_file(str(CONFIG_PATH), "/app/config.yaml", copy=True)
    .env({"PYTHONPATH": "/app/shared"})
)

# Layer 3: ComfyUI installation via comfy-cli (HEAVY, CACHED)
comfy_image = base_image.run_commands(
    f"comfy --skip-prompt install --nvidia --cuda-version {GPU.cuda_version}",
    gpu=GPU.modal_gpu,  # Need GPU for CUDA detection
)

# Layer 4: Template files (LIGHT, changes often)
template_image = (
    comfy_image
    .add_local_dir(str(V3_DIR / "shared"), "/app/shared", copy=True)
    .add_local_dir(str(TEMPLATE_DIR / "workflows"), f"{COMFY_UI_PATH}/user/default/workflows", copy=True)
    .add_local_file(str(CONFIG_PATH), "/app/config.yaml", copy=True)
    .env({
        "PYTHONPATH": "/app/shared",
        "TEMPLATE_NAME": TEMPLATE_NAME,
    })
)

# =============================================================================
# Download Models Function (Uses aria2c for speed)
# =============================================================================
@app.function(
    image=download_image,  # Has aria2c + aiclipse library
    volumes={MODELS_PATH: models_volume},
    secrets=app_secrets,  # R2 + HuggingFace credentials
    timeout=3600,
    memory=4096,  # 4GB for download buffering
)
def download_models():
    """
    Download all models to the persistent volume.
    
    Uses aria2c for blazing fast parallel downloads:
    - 16 connections per file
    - 4 files downloading simultaneously
    - Automatic retry with exponential backoff
    
    Run: modal run v3/templates/qwen-multi-edit/modal/app.py::download_models
    """
    import sys
    import os
    sys.path.insert(0, "/app/shared")
    
    from aiclipse import Config, ModelDownloader
    
    print("=" * 60)
    print("🚀 AiClipse Model Downloader")
    print("=" * 60)
    print(f"📁 Target directory: {MODELS_PATH}")
    print(f"📋 Config: /app/config.yaml")
    print()
    
    # Check existing models
    print("📊 Checking existing models...")
    for subdir in Path(MODELS_PATH).iterdir():
        if subdir.is_dir():
            files = list(subdir.glob("*.safetensors"))
            if files:
                for f in files:
                    size_gb = f.stat().st_size / (1024**3)
                    print(f"   {subdir.name}/{f.name}: {size_gb:.2f} GB")
    print()
    
    config = Config.load("/app/config.yaml")
    print(f"📦 Models to download: {len(config.get_all_models())}")
    for m in config.get_all_models():
        print(f"   - {m.repo}/{Path(m.file).name} -> {m.path}/")
    print()
    
    downloader = ModelDownloader(config, MODELS_PATH)
    result = downloader.download_all()
    
    # Commit volume changes
    print("💾 Committing volume changes...")
    models_volume.commit()
    
    # Summary
    print()
    print("=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"✅ Downloaded: {result.downloaded} models")
    print(f"⏭️  Skipped: {result.skipped} models (already exist)")
    if result.failed > 0:
        print(f"❌ Failed: {result.failed} models")
    print(f"📦 Total Size: {result.total_gb:.2f} GB")
    print(f"⚡ Speed: {result.speed_mbps:.1f} Mbps")
    print(f"⏱️  Duration: {result.duration_seconds:.1f}s")
    print("=" * 60)
    
    return {"downloaded": result.downloaded, "skipped": result.skipped, "failed": result.failed}


# =============================================================================
# Health Check Endpoint
# =============================================================================
@app.function(image=template_image)
@modal.fastapi_endpoint(method="GET", label=f"{TEMPLATE_NAME}-health")
def health():
    """Health check endpoint (no GPU required)."""
    return {"status": "healthy", "template": TEMPLATE_NAME, "gpu": GPU.modal_gpu}


# =============================================================================
# UI Function (Development Mode)
# =============================================================================
@app.function(
    image=template_image,
    gpu=GPU.modal_gpu,
    volumes={
        MODELS_PATH: models_volume,
        OUTPUTS_PATH: outputs_volume,
    },
    timeout=3600,
    memory=32768,  # 32GB
    max_containers=1,  # Single instance for dev
    scaledown_window=300,  # Keep warm 5 min
)
@modal.concurrent(max_inputs=10)
@modal.web_server(port=8188, startup_timeout=120)
def ui():
    """
    Interactive ComfyUI for development.
    
    Run: modal serve v3/templates/qwen-multi-edit/modal/app.py
    """
    import subprocess
    import sys
    sys.path.insert(0, "/app/shared")
    
    from aiclipse import Config, setup_model_paths, install_custom_nodes
    
    print("=" * 60)
    print(f"🎨 Starting AiClipse ComfyUI (UI Mode)")
    print(f"   Template: {TEMPLATE_NAME}")
    print(f"   GPU: {GPU.modal_gpu} ({GPU.vram_gb}GB VRAM)")
    print("=" * 60)
    
    # Load config with env overrides
    config = Config.load("/app/config.yaml")
    
    # Install custom nodes if configured
    if config.template.nodes:
        node_specs = [{"repo": n.repo, "branch": n.branch or "main"} for n in config.template.nodes]
        install_custom_nodes(node_specs, Path(COMFY_UI_PATH))
    
    # Setup model paths
    setup_model_paths(
        comfy_dir=COMFY_UI_PATH,
        models_dir=MODELS_PATH,
        name="modal_volume",
    )
    
    # Symlink outputs to volume
    _setup_output_symlink()
    
    # Build launch command
    comfy_args = " ".join(config.comfy_args) if config.comfy_args else ""
    cmd = f"comfy launch -- --listen 0.0.0.0 --port 8188 {comfy_args}"
    
    print(f"\n🖥️  Running: {cmd}")
    subprocess.Popen(cmd, shell=True, cwd=COMFY_PATH)
    print("✅ ComfyUI started!")


# =============================================================================
# ComfyServer Class (Production API with Memory Snapshot)
# =============================================================================
@app.cls(
    image=template_image,
    gpu=GPU.modal_gpu,
    volumes={
        MODELS_PATH: models_volume,
        OUTPUTS_PATH: outputs_volume,
    },
    secrets=app_secrets,
    timeout=3600,
    memory=32768,  # 32GB
    scaledown_window=300,  # Keep warm 5 min
    max_containers=5,  # Allow scaling for API
    enable_memory_snapshot=True,  # 🔥 Fast cold starts
)
@modal.concurrent(max_inputs=10)
class ComfyServer:
    """
    Production ComfyUI API server with memory snapshot for fast cold starts.
    
    Cold start: ~15-25s (vs ~60-90s without snapshot)
    
    Deploy: modal deploy v3/templates/qwen-multi-edit/modal/app.py
    Serve:  modal serve v3/templates/qwen-multi-edit/modal/app.py
    """
    port: int = 8188
    
    @modal.enter(snap=True)
    def setup_environment(self):
        """
        Snapshot phase: Setup config and paths (NO GPU access).
        
        This runs ONCE and is snapshotted. Future cold starts restore from here.
        """
        import sys
        sys.path.insert(0, "/app/shared")
        
        from aiclipse import Config, setup_model_paths, install_custom_nodes
        
        print("=" * 60)
        print(f"� AiClipse ComfyUI - Snapshot Phase")
        print(f"   Template: {TEMPLATE_NAME}")
        print(f"   GPU: {GPU.modal_gpu} ({GPU.vram_gb}GB VRAM)")
        print("=" * 60)
        
        # Load config (snapshotted)
        self.config = Config.load("/app/config.yaml")
        print(f"📋 Config loaded: {len(self.config.comfy_args)} args")
        
        # Install custom nodes if configured (snapshotted)
        if self.config.template.nodes:
            node_specs = [{"repo": n.repo, "branch": n.branch or "main"} for n in self.config.template.nodes]
            install_custom_nodes(node_specs, Path(COMFY_UI_PATH))
            print(f"📦 Custom nodes: {len(self.config.template.nodes)} installed")
        
        # Setup model paths (snapshotted)
        setup_model_paths(
            comfy_dir=COMFY_UI_PATH,
            models_dir=MODELS_PATH,
            name="modal_volume",
        )
        print(f"📁 Model paths configured")
        
        # Symlink outputs (snapshotted)
        _setup_output_symlink()
        
        print("✅ Snapshot phase complete - environment ready")
    
    @modal.enter(snap=False)
    def launch_server(self):
        """
        Restore phase: Launch server (GPU now available).
        
        This runs AFTER restoring from snapshot. GPU is available.
        """
        import subprocess
        
        print("=" * 60)
        print(f"🚀 AiClipse ComfyUI - Launching Server")
        print("=" * 60)
        
        # Launch server in background with GPU args
        comfy_args = " ".join(self.config.comfy_args) if self.config.comfy_args else ""
        cmd = f"comfy launch --background -- --port {self.port} {comfy_args}"
        
        print(f"🖥️  Running: {cmd}")
        subprocess.run(cmd, shell=True, check=True, cwd=COMFY_PATH)
        print("✅ ComfyUI server started!")
    
    @modal.method()
    def infer(self, workflow_path: str = "/root/workflow_api.json") -> bytes:
        """
        Run a workflow and return output image bytes.
        
        Args:
            workflow_path: Path to workflow JSON file
            
        Returns:
            Image bytes
        """
        import json
        import subprocess
        
        # Health check before running
        self._poll_server_health()
        
        # Run workflow
        cmd = f"comfy run --workflow {workflow_path} --wait --timeout 1200 --verbose"
        subprocess.run(cmd, shell=True, check=True, cwd=COMFY_PATH)
        
        # Find output file
        output_dir = Path(COMFY_UI_PATH) / "output"
        workflow = json.loads(Path(workflow_path).read_text())
        
        # Get filename prefix from SaveImage node
        file_prefix = None
        for node in workflow.values():
            if node.get("class_type") == "SaveImage":
                file_prefix = node.get("inputs", {}).get("filename_prefix")
                break
        
        if not file_prefix:
            file_prefix = "ComfyUI"
        
        # Return first matching file
        for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.name.startswith(file_prefix):
                return f.read_bytes()
        
        raise FileNotFoundError(f"No output file found with prefix: {file_prefix}")
    
    @modal.fastapi_endpoint(method="POST", label=f"{TEMPLATE_NAME}-api")
    def api(self, item: dict):
        """
        Run a workflow via API.
        
        POST body:
        {
            "workflow": {...},  # Optional: workflow JSON
            "prompt": "...",     # Optional: text prompt to inject
            "params": {...}      # Optional: additional parameters
        }
        
        Returns: Image bytes
        """
        import json
        import uuid
        from fastapi import Response
        
        # Load workflow (from request or default)
        if "workflow" in item:
            workflow_data = item["workflow"]
        else:
            # Load default workflow from template
            default_workflow = Path(COMFY_UI_PATH) / "user/default/workflows"
            workflow_files = list(default_workflow.glob("*.json"))
            if workflow_files:
                workflow_data = json.loads(workflow_files[0].read_text())
            else:
                return {"error": "No workflow provided and no default found"}
        
        # Inject prompt if provided
        if "prompt" in item:
            for node in workflow_data.values():
                if node.get("class_type") in ["CLIPTextEncode", "Text"]:
                    if "text" in node.get("inputs", {}):
                        node["inputs"]["text"] = item["prompt"]
                        break
        
        # Apply params if provided
        if "params" in item:
            for node_id, params in item["params"].items():
                if node_id in workflow_data:
                    workflow_data[node_id]["inputs"].update(params)
        
        # Generate unique ID for this request
        client_id = uuid.uuid4().hex[:8]
        
        # Set unique filename prefix
        for node in workflow_data.values():
            if node.get("class_type") == "SaveImage":
                node["inputs"]["filename_prefix"] = client_id
        
        # Save workflow to temp file
        workflow_file = f"/tmp/{client_id}.json"
        with open(workflow_file, "w") as f:
            json.dump(workflow_data, f)
        
        # Run inference
        try:
            img_bytes = self.infer.local(workflow_file)
            return Response(img_bytes, media_type="image/png")
        except Exception as e:
            return {"error": str(e)}
    
    def _poll_server_health(self):
        """Check if ComfyUI server is healthy, stop container if not."""
        import socket
        import urllib.request
        
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/system_stats")
            urllib.request.urlopen(req, timeout=5)
            print("✅ ComfyUI server is healthy")
        except (socket.timeout, urllib.error.URLError) as e:
            print(f"❌ Server health check failed: {e}")
            modal.experimental.stop_fetching_inputs()
            raise Exception("ComfyUI server is not healthy, stopping container")


# =============================================================================
# Helper Functions
# =============================================================================
def _setup_output_symlink():
    """Symlink ComfyUI output to volume."""
    import shutil
    
    comfy_output = Path(COMFY_UI_PATH) / "output"
    if comfy_output.exists() and not comfy_output.is_symlink():
        shutil.rmtree(comfy_output)
    if not comfy_output.exists():
        comfy_output.parent.mkdir(parents=True, exist_ok=True)
        comfy_output.symlink_to(OUTPUTS_PATH)
        print(f"🔗 Outputs → {OUTPUTS_PATH}")


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    print("Usage:")
    print("  Development: modal serve v3/templates/qwen-multi-edit/modal/app.py::ui")
    print("  Production:  modal deploy v3/templates/qwen-multi-edit/modal/app.py")
    print("")
    print("Endpoints after deploy:")
    print(f"  - GET  /{TEMPLATE_NAME}-health   Health check")
    print(f"  - POST /{TEMPLATE_NAME}-api      Run workflow via API")

