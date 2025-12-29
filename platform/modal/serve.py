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

DEFAULT_TEMPLATE = os.environ.get("AICLIPSE_TEMPLATE", "qwen-multi-edit")
GHCR_ORG = "ghcr.io/nishit-g"

# Template -> GHCR image mapping
TEMPLATE_IMAGES = {
    "boomboom": f"{GHCR_ORG}/aiclipse-boomboom:rtx5090-latest",
    "sd15-basic": f"{GHCR_ORG}/aiclipse-sd15-basic:rtx5090-latest",
    "qwen-multi-edit": f"{GHCR_ORG}/aiclipse-qwen-multi-edit:rtx5090-latest",
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
    # Don't add_python - GHCR image already has Python
    return modal.Image.from_registry(ghcr_url).entrypoint([])


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
    max_containers=1,  # ComfyUI is stateful, only 1 container needed
    enable_memory_snapshot=True,  # Snapshot for faster cold starts
)
class ComfyUI:
    """
    Best-in-class ComfyUI server.
    
    - Reads config from templates/*/config.yaml (same as RunPod)
    - Sets proper env vars for start.sh
    - Uses pre-downloaded models from Volume
    - Memory snapshots for fast cold starts
    
    Note: No @concurrent decorator - ComfyUI is a stateful web server
    that handles its own request queuing internally.
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
        # COMMENTED OUT: Brace expansion fix no longer needed
        # The common.dockerfile has been fixed to not create model directories.
        # ComfyUI creates its own models/ subdirs, and extra_model_paths.yaml
        # points to the Modal Volume for external models.
        # =====================================================================
        # self._fix_brace_expansion_bug()  # Disabled - Docker build fixed
        
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
            self._setup_extra_model_paths()
            
            # Skip downloads since models are ready
            os.environ["SKIP_MODEL_DOWNLOAD"] = "true"
            os.environ["DOWNLOAD_MODELS"] = "false"
        else:
            print("[MODAL] ⚠️ No pre-downloaded models in Volume")
            print("[MODAL] ℹ️ Run: modal run platform/modal/download.py --template boomboom")
            os.environ["DOWNLOAD_MODELS"] = "true"
        
        print("=" * 60)
    
    def _fix_brace_expansion_bug(self):
        """
        Fix directories created with literal brace syntax due to Dockerfile bug.
        Old images created dirs like "{ComfyUI,models}" instead of separate dirs.
        """
        import shutil
        
        print("[MODAL] 🔧 Running brace expansion fix...")
        
        workspace = Path("/workspace/aiclipse")
        comfy_models = Path("/workspace/aiclipse/models")
        comfy_dir = Path("/workspace/aiclipse/ComfyUI")
        
        # Debug: show what exists in workspace
        if workspace.exists():
            print(f"[MODAL] 📂 Contents of {workspace}:")
            for item in sorted(workspace.iterdir()):
                print(f"[MODAL]    - {item.name} ({'dir' if item.is_dir() else 'file'})")
        
        # Check for and remove malformed brace directories
        brace_patterns = [
            (workspace, "{ComfyUI,models,workflows,output,logs,temp}"),
            (comfy_models, "{checkpoints,diffusion_models,vae,loras,clip,controlnet,upscale_models,embeddings}"),
        ]
        
        fixed = False
        for parent, bad_name in brace_patterns:
            bad_path = parent / bad_name
            if bad_path.exists():
                print(f"[MODAL] 🔧 Removing malformed directory: {bad_path}")
                shutil.rmtree(bad_path, ignore_errors=True)
                fixed = True
        
        # Create proper directory structure
        workspace_dirs = ["ComfyUI", "models", "workflows", "output", "logs", "temp"]
        for d in workspace_dirs:
            (workspace / d).mkdir(parents=True, exist_ok=True)
        print(f"[MODAL] ✅ Created workspace directories: {workspace_dirs}")
        
        model_dirs = [
            "checkpoints", "diffusion_models", "vae", "loras", "clip",
            "controlnet", "upscale_models", "embeddings", "unet",
            "text_encoders", "hypernetworks", "clip_vision", "style_models", "gligen"
        ]
        for d in model_dirs:
            (comfy_models / d).mkdir(parents=True, exist_ok=True)
        print(f"[MODAL] ✅ Created {len(model_dirs)} model directories")
        
        # Debug: show models dir contents now
        if comfy_models.exists():
            print(f"[MODAL] 📂 Contents of {comfy_models}:")
            for item in sorted(comfy_models.iterdir()):
                print(f"[MODAL]    - {item.name}")
        
        # Ensure ComfyUI models symlink points to our models dir
        comfy_models_link = comfy_dir / "models"
        if comfy_models_link.exists() and not comfy_models_link.is_symlink():
            # It's a real directory, move contents and replace with symlink
            print(f"[MODAL] 🔧 Converting ComfyUI/models to symlink")
            for item in comfy_models_link.iterdir():
                dest = comfy_models / item.name
                if not dest.exists():
                    shutil.move(str(item), str(dest))
            shutil.rmtree(comfy_models_link)
        
        if not comfy_models_link.exists():
            comfy_models_link.symlink_to(comfy_models)
            print(f"[MODAL] 🔗 Created symlink: {comfy_models_link} → {comfy_models}")
        elif comfy_models_link.is_symlink():
            print(f"[MODAL] 🔗 Symlink exists: {comfy_models_link} → {comfy_models_link.resolve()}")
        
        if fixed:
            print("[MODAL] ✅ Fixed brace expansion bug from old Docker image")
    
    def _setup_extra_model_paths(self):
        """
        Create extra_model_paths.yaml for ComfyUI to find Volume models.
        This is more reliable than symlinks in containerized environments.
        """
        volume_models = Path(MODELS_VOLUME_PATH)
        comfy_dir = Path("/workspace/aiclipse/ComfyUI")
        yaml_path = comfy_dir / "extra_model_paths.yaml"
        
        # Debug: show what's in the volume
        print(f"\n[MODAL] 📦 Checking Modal Volume at: {MODELS_VOLUME_PATH}")
        if volume_models.exists():
            for subdir in sorted(volume_models.iterdir()):
                if subdir.is_dir():
                    files = list(subdir.glob("*"))
                    if files:
                        print(f"[MODAL]    ✅ {subdir.name}/: {len(files)} file(s)")
                    # Create empty dirs so ComfyUI UI shows all folders
                    else:
                        print(f"[MODAL]    📁 {subdir.name}/: (empty)")
        
        # Create YAML config - string-based for precise formatting
        # NOTE: unet models are loaded via diffusion_models, so we include both paths
        config = f"""# Auto-generated by Modal v1 serve.py
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
    hypernetworks: hypernetworks/
    clip_vision: clip_vision/
    style_models: style_models/
    gligen: gligen/
"""
        yaml_path.write_text(config)
        print(f"[MODAL] ✅ Created {yaml_path}")
    
    def _setup_model_symlinks(self):
        """
        Legacy approach: Symlink Volume models to ComfyUI paths.
        Kept as fallback if extra_model_paths.yaml doesn't work.
        """
        comfy_models = Path("/workspace/aiclipse/models")
        volume_models = Path(MODELS_VOLUME_PATH)
        
        subdirs = [
            "checkpoints", "unet", "vae", "loras", 
            "text_encoders", "embeddings", "controlnet",
            "diffusion_models", "clip", "upscale_models"
        ]
        
        for subdir in subdirs:
            vol_path = volume_models / subdir
            comfy_path = comfy_models / subdir
            
            if vol_path.exists() and any(vol_path.iterdir()):
                comfy_path.parent.mkdir(parents=True, exist_ok=True)
                
                if comfy_path.is_symlink():
                    comfy_path.unlink()
                elif comfy_path.exists():
                    shutil.rmtree(comfy_path)
                
                comfy_path.symlink_to(vol_path)
                file_count = len(list(vol_path.glob("*")))
                print(f"[MODAL] 🔗 Symlinked {subdir}/ ({file_count} files)")
    
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
