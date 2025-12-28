"""
AiClipse ComfyUI - Best-in-Class Modal Server
==============================================

Config-driven deployment that reads the SAME templates/*/config.yaml
files as RunPod. Unified configuration across platforms.

Key Features:
- Reads config.yaml from templates/ (same as RunPod)
- Sets proper env vars for start.sh (TEMPLATE_TYPE, MODELS_MANIFEST, etc.)
- GPU mapping from config.gpu_requirement
- Pre-downloaded models in Volume with smart symlinks
- Memory snapshots for fast cold starts
- Health check endpoint

Usage:
    # Pre-download models to Volume (CPU, cheap!)
    modal run platform/modal/download.py::main --template boomboom
    
    # Dev mode
    modal serve platform/modal/serve.py
    
    # Production
    modal deploy platform/modal/serve.py
"""
import modal
import subprocess
import os
import shutil
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TEMPLATE = os.environ.get("AICLIPSE_TEMPLATE", "boomboom")
GHCR_ORG = "ghcr.io/nishit-g"

# Template -> GHCR image mapping
TEMPLATE_IMAGES = {
    "boomboom": f"{GHCR_ORG}/aiclipse-boomboom:rtx5090-main",
    "sd15-basic": f"{GHCR_ORG}/aiclipse-sd15-basic:rtx5090-main",
}

# GPU requirement -> Modal GPU
GPU_MAPPING = {
    "12GB": "T4", "16GB": "L4", "24GB": "A10G",
    "40GB": "A100", "48GB": "L40S", "80GB": "A100",
}

# Volume paths
MODELS_VOLUME_PATH = "/modal-volumes/models"
OUTPUTS_VOLUME_PATH = "/modal-volumes/outputs"
WORKFLOWS_VOLUME_PATH = "/modal-volumes/workflows"

# =============================================================================
# Config Loader (reads same config.yaml as RunPod)
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
    # Look for config in multiple locations
    candidates = [
        Path(f"/config/config.yaml"),  # Mounted by Docker/Modal
        Path(f"/templates/{template}/config.yaml"),  # Direct path
        Path(__file__).parent.parent.parent / "templates" / template / "config.yaml",
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
    
    # Fallback: check for manifest files
    manifest_bases = [
        Path(f"/manifests/{template}_models.txt"),
        Path(f"/manifests/boomboom_models.txt"),
    ]
    
    models_manifest = next((p for p in manifest_bases if p.exists()), None)
    
    return TemplateConfig(
        name=template,
        models_manifest=str(models_manifest) if models_manifest else None,
    )


def get_modal_gpu(config: TemplateConfig) -> str:
    """Map config.gpu_requirement to Modal GPU type."""
    return GPU_MAPPING.get(config.gpu_requirement, "L40S")


# =============================================================================
# Modal App
# =============================================================================

app = modal.App("aiclipse-comfyui")

# Persistent Volumes
models_volume = modal.Volume.from_name("aiclipse-models", create_if_missing=True)
outputs_volume = modal.Volume.from_name("aiclipse-outputs", create_if_missing=True)
workflows_volume = modal.Volume.from_name("aiclipse-workflows", create_if_missing=True)


def get_image(template: str) -> modal.Image:
    """Get GHCR image for template."""
    ghcr_url = TEMPLATE_IMAGES.get(template, TEMPLATE_IMAGES["boomboom"])
    return modal.Image.from_registry(ghcr_url, add_python="3.12").entrypoint([])


def get_volume_mounts():
    """Volume mount configuration."""
    return {
        MODELS_VOLUME_PATH: models_volume,
        OUTPUTS_VOLUME_PATH: outputs_volume,
        WORKFLOWS_VOLUME_PATH: workflows_volume,
    }


# Load config at import time (for decorators)
_config = load_template_config(DEFAULT_TEMPLATE)
_gpu = get_modal_gpu(_config)

# =============================================================================
# ComfyUI Server
# =============================================================================

@app.cls(
    image=get_image(DEFAULT_TEMPLATE),
    gpu=_gpu,
    volumes=get_volume_mounts(),
    timeout=3600,
    scaledown_window=300,
    min_containers=0,
    enable_memory_snapshot=True,
)
@modal.concurrent(max_inputs=5)
class ComfyUI:
    """
    Best-in-class ComfyUI server.
    
    - Reads config from templates/*/config.yaml (same as RunPod)
    - Sets proper env vars for start.sh
    - Uses pre-downloaded models from Volume
    - Memory snapshots for fast cold starts
    """
    
    @modal.enter()
    def setup(self):
        """Configure environment before serving requests."""
        print("=" * 60)
        print("[MODAL] AiClipse ComfyUI - Enterprise Server")
        print("=" * 60)
        
        config = load_template_config(DEFAULT_TEMPLATE)
        print(f"[MODAL] Template: {config.name} v{config.version}")
        print(f"[MODAL] GPU Requirement: {config.gpu_requirement}")
        
        # =====================================================================
        # SET ENV VARS (same as RunPod!)
        # These are read by start.sh and its modules
        # =====================================================================
        
        os.environ["TEMPLATE_TYPE"] = config.name
        os.environ["TEMPLATE_VERSION"] = config.version
        
        # ComfyUI arguments
        if config.comfy_args:
            os.environ["COMFY_ARGS"] = " ".join(config.comfy_args)
            print(f"[MODAL] COMFY_ARGS: {os.environ['COMFY_ARGS']}")
        
        # =====================================================================
        # VOLUME INTEGRATION
        # Set paths for start.sh to discover pre-downloaded models
        # =====================================================================
        
        # Create Volume directories
        Path(MODELS_VOLUME_PATH).mkdir(parents=True, exist_ok=True)
        Path(OUTPUTS_VOLUME_PATH).mkdir(parents=True, exist_ok=True)
        Path(WORKFLOWS_VOLUME_PATH).mkdir(parents=True, exist_ok=True)
        
        # Tell scripts where models are
        os.environ["MODAL_MODELS_PATH"] = MODELS_VOLUME_PATH
        os.environ["MODAL_OUTPUTS_PATH"] = OUTPUTS_VOLUME_PATH
        
        # Count pre-downloaded models
        model_files = list(Path(MODELS_VOLUME_PATH).rglob("*.safetensors"))
        model_count = len(model_files)
        
        if model_count > 0:
            print(f"[MODAL] ✅ Found {model_count} pre-downloaded models in Volume")
            
            # Create symlinks from Volume to expected model paths
            self._setup_model_symlinks()
            
            # Skip downloads since models are ready
            os.environ["SKIP_MODEL_DOWNLOAD"] = "true"
            os.environ["DOWNLOAD_MODELS"] = "false"
        else:
            print("[MODAL] ⚠️ No pre-downloaded models in Volume")
            print("[MODAL] ℹ️ Run: modal run platform/modal/download.py --template boomboom")
            os.environ["DOWNLOAD_MODELS"] = "true"
        
        print("=" * 60)
    
    def _setup_model_symlinks(self):
        """
        Symlink Volume models to ComfyUI expected paths.
        This avoids re-downloading and uses pre-cached models.
        """
        comfy_models = Path("/workspace/aiclipse/models")
        volume_models = Path(MODELS_VOLUME_PATH)
        
        # Model subdirectories to link
        subdirs = [
            "checkpoints", "unet", "vae", "loras", 
            "text_encoders", "embeddings", "controlnet",
            "diffusion_models", "clip", "upscale_models"
        ]
        
        for subdir in subdirs:
            vol_path = volume_models / subdir
            comfy_path = comfy_models / subdir
            
            if vol_path.exists() and any(vol_path.iterdir()):
                # Has files, create symlink
                comfy_path.parent.mkdir(parents=True, exist_ok=True)
                
                if comfy_path.is_symlink():
                    comfy_path.unlink()
                elif comfy_path.exists():
                    shutil.rmtree(comfy_path)
                
                comfy_path.symlink_to(vol_path)
                file_count = len(list(vol_path.glob("*")))
                print(f"[MODAL] 🔗 Linked {subdir}/ ({file_count} files)")
    
    @modal.web_server(port=8188, startup_timeout=600)
    def serve(self):
        """Start ComfyUI via the standard start.sh script."""
        print("[MODAL] Starting ComfyUI with /scripts/start.sh...")
        subprocess.Popen(["bash", "/scripts/start.sh"])
    
    @modal.method()
    def health(self) -> dict:
        """Health check endpoint."""
        import urllib.request
        try:
            response = urllib.request.urlopen("http://localhost:8188/system_stats", timeout=5)
            return {"status": "healthy", "comfyui": "running"}
        except:
            return {"status": "starting", "comfyui": "initializing"}


# =============================================================================
# CLI Entrypoint
# =============================================================================

@app.local_entrypoint()
def main(template: str = DEFAULT_TEMPLATE):
    """Show deployment info."""
    print("=" * 60)
    print("AiClipse ComfyUI - Modal Enterprise Server")
    print("=" * 60)
    
    try:
        config = load_template_config(template)
        print(f"Template: {config.name} v{config.version}")
        print(f"GPU: {config.gpu_requirement} → Modal {get_modal_gpu(config)}")
        if config.comfy_args:
            print(f"Args: {' '.join(config.comfy_args)}")
    except Exception as e:
        print(f"Template: {template} (config not found locally)")
    
    print()
    print("Commands:")
    print("  modal run platform/modal/download.py --template boomboom  # Pre-download models")
    print("  modal serve platform/modal/serve.py   # Dev mode")
    print("  modal deploy platform/modal/serve.py  # Production")
    print("=" * 60)
