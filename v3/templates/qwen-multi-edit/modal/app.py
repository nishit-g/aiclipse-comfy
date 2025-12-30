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
GPU_VARIANT = os.environ.get("GPU_VARIANT", "l40s")
GPU = get_gpu_config(GPU_VARIANT)

# Volume names (v2 volumes for better performance)
# v2 benefits: unlimited files, hundreds of concurrent writers, faster commits/reloads
MODELS_VOLUME_NAME = "aiclipse-models-v2"
OUTPUTS_VOLUME_NAME = "aiclipse-outputs-v2"
INPUTS_VOLUME_NAME = "aiclipse-inputs-v2"

# Paths inside container
MODELS_PATH = "/models"
OUTPUTS_PATH = "/outputs"
INPUTS_PATH = "/inputs"
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
inputs_volume = modal.Volume.from_name(INPUTS_VOLUME_NAME, create_if_missing=True)

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
# Serve Function (Unified UI + API)
# =============================================================================
@app.function(
    image=template_image,
    gpu=GPU.modal_gpu,
    volumes={
        MODELS_PATH: models_volume,
        OUTPUTS_PATH: outputs_volume,
        INPUTS_PATH: inputs_volume,  # Shared input images
    },
    secrets=app_secrets,
    timeout=3600,
    memory=32768,  # 32GB
    max_containers=5,  # Allow auto-scaling
    scaledown_window=60,  # Keep warm 1 min
    enable_memory_snapshot=True,  # 🔥 Fast cold starts
)
@modal.concurrent(max_inputs=10)
@modal.web_server(port=8188, startup_timeout=120, requires_proxy_auth=True)
def serve():
    """
    Unified ComfyUI Server - Single endpoint for UI and API.
    
    Development: modal serve v3/templates/qwen-multi-edit/modal/app.py::serve
    Production:  modal deploy v3/templates/qwen-multi-edit/modal/app.py
    
    Input images:
        Upload to volume: modal volume put aiclipse-inputs-v2 myimage.png
        Reference in workflow as: myimage.png
    
    Native ComfyUI APIs:
        POST /prompt         - Queue a workflow
        GET  /history/{id}   - Get execution results
        WS   /ws             - Real-time progress + results
        POST /upload/image   - Upload input images (per-container)
        GET  /system_stats   - Health check
    """
    import subprocess
    import sys
    sys.path.insert(0, "/app/shared")
    
    from aiclipse import Config, setup_model_paths, install_custom_nodes
    
    print("=" * 60)
    print(f"🚀 AiClipse ComfyUI Server")
    print(f"   Template: {TEMPLATE_NAME}")
    print(f"   GPU: {GPU.modal_gpu} ({GPU.vram_gb}GB VRAM)")
    print("=" * 60)
    
    # Load config with env overrides
    config = Config.load("/app/config.yaml")
    
    # Install custom nodes if configured
    if config.template.nodes:
        node_specs = [{"repo": n.repo, "branch": n.branch or "main"} for n in config.template.nodes]
        install_custom_nodes(node_specs, Path(COMFY_UI_PATH))
        print(f"📦 Custom nodes: {len(config.template.nodes)} installed")
    
    # Setup model paths
    setup_model_paths(
        comfy_dir=COMFY_UI_PATH,
        models_dir=MODELS_PATH,
        name="modal_volume",
    )
    
    # Setup symlinks for volumes
    _setup_output_symlink()
    _setup_input_symlink()
    
    # Build launch command
    comfy_args = " ".join(config.comfy_args) if config.comfy_args else ""
    cmd = f"comfy launch -- --listen 0.0.0.0 --port 8188 {comfy_args}"
    
    print(f"\n🖥️  Running: {cmd}")
    subprocess.Popen(cmd, shell=True, cwd=COMFY_PATH)
    print("✅ ComfyUI started!")
    print("\n📚 Docs: https://docs.comfy.org/essentials/comfyui_as_api")


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


def _setup_input_symlink():
    """Symlink ComfyUI input to volume for shared input images."""
    import shutil
    
    comfy_input = Path(COMFY_UI_PATH) / "input"
    if comfy_input.exists() and not comfy_input.is_symlink():
        shutil.rmtree(comfy_input)
    if not comfy_input.exists():
        comfy_input.parent.mkdir(parents=True, exist_ok=True)
        comfy_input.symlink_to(INPUTS_PATH)
        print(f"🔗 Inputs → {INPUTS_PATH}")


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    print("AiClipse ComfyUI Server")
    print("=" * 40)
    print("")
    print("Commands:")
    print("  Development: modal serve v3/templates/qwen-multi-edit/modal/app.py::serve")
    print("  Production:  modal deploy v3/templates/qwen-multi-edit/modal/app.py")
    print("")
    print("Input Images (shared across containers):")
    print("  modal volume put aiclipse-inputs-v2 myimage.png")
    print("")
    print("After deploy, use native ComfyUI API:")
    print("  POST /prompt         - Queue workflow")
    print("  WS   /ws             - WebSocket for real-time results")
    print("  GET  /history/{id}   - Get execution results")

