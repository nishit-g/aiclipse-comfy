"""
AiClipse ComfyUI V2 - Modal-Native Server
==========================================

Rebuilt from scratch following official Modal best practices.
No external Docker images - pure Modal native image building.

Key Changes from v1:
- Uses Modal-native image building (no GHCR dependency)
- Uses comfy-cli for ComfyUI installation
- Follows Modal Labs official documentation patterns
- Simpler, more maintainable code

Usage:
    # Dev mode
    modal serve platform/modal/v2/serve.py
    
    # Production
    modal deploy platform/modal/v2/serve.py
"""
import subprocess
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import modal

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TEMPLATE = os.environ.get("AICLIPSE_TEMPLATE", "qwen-multi-edit")

# GPU requirement -> Modal GPU mapping
GPU_MAPPING = {
    "12GB": "T4",
    "16GB": "L4", 
    "24GB": "A10G",
    "40GB": "A100-40GB",
    "48GB": "L40S",
    "80GB": "A100-80GB",
}

# Volume paths
MODELS_VOLUME_PATH = "/modal-volumes/models"
OUTPUTS_VOLUME_PATH = "/modal-volumes/outputs"
# NOTE: comfy-cli installs ComfyUI to /root/comfy (not /root/comfy/ComfyUI)
# The extra_model_paths.yaml must be in the same directory as main.py
COMFY_PATH = "/root/comfy"

# =============================================================================
# Template Config Loading (same as v1 - reads templates/*/config.yaml)
# =============================================================================

@dataclass
class TemplateConfig:
    """Template configuration from config.yaml."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    gpu_requirement: str = "24GB"
    comfy_args: list = field(default_factory=list)
    models_manifest: Optional[str] = None
    nodes_manifest: Optional[str] = None


def load_template_config(template: str) -> TemplateConfig:
    """Load config.yaml from template directory."""
    candidates = [
        Path(__file__).parent.parent.parent / "templates" / template / "config.yaml",
        Path(f"/templates/{template}/config.yaml"),
    ]
    
    for config_path in candidates:
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
            
            return TemplateConfig(
                name=data.get("name", template),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                gpu_requirement=data.get("gpu_requirement", "24GB"),
                comfy_args=data.get("comfy_args", []),
            )
    
    # Fallback
    return TemplateConfig(name=template, gpu_requirement="24GB")


def get_modal_gpu(config: TemplateConfig) -> str:
    """Map config.gpu_requirement to Modal GPU type."""
    return GPU_MAPPING.get(config.gpu_requirement, "L40S")


# =============================================================================
# Modal Image Building - Following Modal Best Practices
# =============================================================================

# CUDA base for better GPU support
cuda_version = "12.8.1"
flavor = "cudnn-devel"
operating_sys = "ubuntu24.04"
cuda_tag = f"{cuda_version}-{flavor}-{operating_sys}"

# Build the image step by step
base_image = (
    modal.Image.from_registry(f"nvidia/cuda:{cuda_tag}", add_python="3.12")
    .entrypoint([])  # Remove CUDA image's verbose entrypoint
    .apt_install(
        "git", "wget", "rsync", "curl",
        "libgl1", "libglib2.0-0",  # For OpenCV
        "ffmpeg",  # For video processing
    )
    .pip_install(
        # Core dependencies
        "torch>=2.5.0",
        "torchvision",
        "torchaudio",
        # ComfyUI tools
        "comfy-cli==1.5.3",
        # Utilities
        "huggingface-hub>=0.26.0",
        "hf_transfer",
        "safetensors",
        "aiohttp",
        "pyyaml",
        # FastAPI for health endpoint
        "fastapi[standard]",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "PYTHONUNBUFFERED": "1",
    })
)

# Install ComfyUI with comfy-cli (correct syntax: comfy --workspace=/path install)
comfy_image = base_image.run_commands(
    "comfy --skip-prompt --workspace=/root/comfy install --fast-deps --nvidia --version 0.6.0",
    "mkdir -p /root/comfy/ComfyUI/user/default/workflows",
    gpu="A10G",  # Use GPU during build for proper CUDA detection
)

# Copy local workflow files from templates
LOCAL_TEMPLATE = Path(__file__).parent.parent.parent / "templates" / DEFAULT_TEMPLATE
LOCAL_WORKFLOWS = LOCAL_TEMPLATE / "workflows"
LOCAL_CONFIG = LOCAL_TEMPLATE / "config.yaml"

if LOCAL_WORKFLOWS.exists():
    comfy_image = comfy_image.add_local_dir(
        str(LOCAL_WORKFLOWS),
        remote_path=f"{COMFY_PATH}/user/default/workflows",
    )

if LOCAL_CONFIG.exists():
    comfy_image = comfy_image.add_local_file(
        str(LOCAL_CONFIG),
        remote_path=f"/config/config.yaml",
    )

# =============================================================================
# Modal App
# =============================================================================

app = modal.App(name="aiclipse-comfyui-v2", image=comfy_image)

# Persistent Volumes
models_volume = modal.Volume.from_name("aiclipse-models", create_if_missing=True)
outputs_volume = modal.Volume.from_name("aiclipse-outputs", create_if_missing=True)

# Load config at import time for decorator parameters
_config = load_template_config(DEFAULT_TEMPLATE)
_gpu = get_modal_gpu(_config)


def create_extra_model_paths():
    """Create extra_model_paths.yaml for ComfyUI to find models in Volume."""
    # Debug: show what's actually in the volume
    volume_path = Path(MODELS_VOLUME_PATH)
    print(f"\n📦 Checking Modal Volume at: {MODELS_VOLUME_PATH}")
    
    if volume_path.exists():
        for subdir in volume_path.iterdir():
            if subdir.is_dir():
                files = list(subdir.glob("*"))
                if files:
                    print(f"   ✅ {subdir.name}/: {len(files)} file(s)")
                    for f in files[:3]:  # Show first 3 files
                        print(f"      - {f.name}")
                else:
                    print(f"   📁 {subdir.name}/: (empty)")
    else:
        print(f"   ⚠️ Volume path does not exist!")
    
    # Create YAML config - using proper format matching ComfyUI's expected structure
    # Note: paths are RELATIVE to base_path
    # NOTE: In ComfyUI, 'unet' models are loaded via 'diffusion_models' loader
    # So we add unet/ as an additional path for diffusion_models using YAML multi-line
    config = f"""# Auto-generated by Modal v2 serve.py
# This tells ComfyUI to look for additional models in the Modal Volume
modal_volume:
    base_path: {MODELS_VOLUME_PATH}
    checkpoints: checkpoints/
    diffusion_models: |
        diffusion_models/
        unet/
    unet: unet/
    vae: vae/
    loras: loras/
    text_encoders: text_encoders/
    clip: clip/
    controlnet: controlnet/
    upscale_models: upscale_models/
    embeddings: embeddings/
"""
    config_path = f"{COMFY_PATH}/extra_model_paths.yaml"
    Path(config_path).write_text(config)
    print(f"✅ Created {config_path}")


def setup_output_symlinks():
    """Symlink outputs to persistent volume."""
    output_dir = Path(f"{COMFY_PATH}/output")
    volume_output = Path(f"{OUTPUTS_VOLUME_PATH}/generations")
    
    volume_output.mkdir(parents=True, exist_ok=True)
    
    if output_dir.exists() and not output_dir.is_symlink():
        # Move existing outputs to volume
        import shutil
        for item in output_dir.iterdir():
            shutil.move(str(item), str(volume_output / item.name))
        output_dir.rmdir()
    
    if not output_dir.exists():
        output_dir.symlink_to(volume_output)
        print(f"✅ Linked outputs to {volume_output}")


# =============================================================================
# ComfyUI Server Function
# =============================================================================

@app.function(
    gpu=_gpu,
    memory=32768,
    timeout=3600,
    volumes={
        MODELS_VOLUME_PATH: models_volume,
        OUTPUTS_VOLUME_PATH: outputs_volume,
    },
    # Autoscaling settings
    min_containers=0,
    scaledown_window=300,  # Keep warm for 5 minutes
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8188, startup_timeout=300)
def serve():
    """
    Serve ComfyUI with full GPU acceleration.
    
    This function is called once per container startup.
    ComfyUI then handles multiple requests via @modal.concurrent.
    """
    import time
    
    print("=" * 60)
    print("🚀 Starting AiClipse ComfyUI V2")
    print(f"   Template: {DEFAULT_TEMPLATE}")
    print(f"   GPU: {_gpu}")
    print("=" * 60)
    
    # Setup model paths
    create_extra_model_paths()
    
    # Setup output persistence
    setup_output_symlinks()
    
    # List available models
    models_path = Path(MODELS_VOLUME_PATH)
    if models_path.exists():
        print(f"\n📦 Models in volume:")
        for category in models_path.iterdir():
            if category.is_dir():
                count = len(list(category.glob("*")))
                print(f"   {category.name}: {count} file(s)")
    else:
        print(f"\n⚠️ Models volume empty at {MODELS_VOLUME_PATH}")
    
    # Build comfy args
    comfy_args = " ".join(_config.comfy_args) if _config.comfy_args else ""
    
    # Start ComfyUI
    cmd = f"comfy launch -- --listen 0.0.0.0 --port 8188 {comfy_args}"
    print(f"\n🖥️  Running: {cmd}")
    
    subprocess.Popen(
        cmd,
        shell=True,
        cwd=COMFY_PATH,
    )
    
    print("\n✅ ComfyUI started successfully!")


# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.function()
@modal.fastapi_endpoint(method="GET", label="health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "template": DEFAULT_TEMPLATE,
        "version": _config.version,
        "gpu": _gpu,
    }


# =============================================================================
# Model Download Utility (runs on CPU, cheap!)
# =============================================================================

@app.function(
    timeout=7200,
    volumes={MODELS_VOLUME_PATH: models_volume},
    cpu=2.0,
    memory=8192,
)
def download_models(
    repo_id: str,
    filename: str | None = None,
    subfolder: str = ".",
):
    """
    Download models from HuggingFace to the models volume.
    
    Usage:
        modal run platform/modal/v2/serve.py::download_models \\
            --repo-id "Comfy-Org/Qwen_QwQ-32B-Preview_ComfyUI" \\
            --subfolder "diffusion_models"
    """
    from huggingface_hub import snapshot_download, hf_hub_download
    
    dest_path = Path(MODELS_VOLUME_PATH) / subfolder
    dest_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📥 Downloading from {repo_id}")
    print(f"   Destination: {dest_path}")
    
    if filename:
        # Download specific file
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(dest_path),
        )
        print(f"✅ Downloaded {filename}")
    else:
        # Download entire repo
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest_path),
        )
        print(f"✅ Downloaded entire repo")
    
    # Commit changes to volume
    models_volume.commit()
    print("💾 Volume committed")


# =============================================================================
# CLI Entrypoint
# =============================================================================

@app.local_entrypoint()
def main():
    """Display help for the v2 Modal app."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         AiClipse ComfyUI V2 - Modal Native                     ║
╠════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  USAGE:                                                         ║
║                                                                 ║
║  # Development (hot reload)                                     ║
║  modal serve platform/modal/v2/serve.py                         ║
║                                                                 ║
║  # Production deployment                                        ║
║  modal deploy platform/modal/v2/serve.py                        ║
║                                                                 ║
║  # Download models to volume                                    ║
║  modal run platform/modal/v2/serve.py::download_models \\        ║
║      --repo-id "Comfy-Org/Qwen_QwQ-32B-Preview_ComfyUI"         ║
║                                                                 ║
╚════════════════════════════════════════════════════════════════╝
    """)
