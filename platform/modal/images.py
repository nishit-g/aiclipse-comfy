"""
Modal Image Definitions
=======================
Base images and template-specific images for ComfyUI.
"""
import modal
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

# GHCR base images (your existing Docker images)
GHCR_ORG = "ghcr.io/nishit-g"

TEMPLATE_IMAGES = {
    "boomboom": f"{GHCR_ORG}/aiclipse-boomboom:rtx5090-main",
    "sd15-basic": f"{GHCR_ORG}/aiclipse-sd15-basic:rtx5090-main",
    # Add more templates as needed
}

DEFAULT_TEMPLATE = "boomboom"

# =============================================================================
# Base Image for CPU Downloads (lightweight)
# =============================================================================

download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("aria2", "git", "curl")
    .pip_install(
        "huggingface-hub[hf_xet]",
        "boto3",
        "requests",
        "pyyaml",
        "tqdm",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_XET_HIGH_PERFORMANCE": "1",
    })
)

# =============================================================================
# ComfyUI Image (from existing GHCR)
# =============================================================================

def get_comfyui_image(template: str = DEFAULT_TEMPLATE) -> modal.Image:
    """
    Get the ComfyUI image for a specific template.
    Uses your existing GHCR Docker images.
    """
    if template not in TEMPLATE_IMAGES:
        raise ValueError(f"Unknown template: {template}. Available: {list(TEMPLATE_IMAGES.keys())}")
    
    ghcr_url = TEMPLATE_IMAGES[template]
    
    return (
        modal.Image.from_registry(ghcr_url, add_python="3.12")
        .entrypoint([])  # Clear entrypoint for Modal control
    )

# =============================================================================
# GPU Mapping
# =============================================================================

GPU_MAPPING = {
    "12GB": "T4",      # Budget option
    "16GB": "L4",      # Good for SD 1.5
    "24GB": "A10G",    # Good for SDXL
    "48GB": "L40S",    # Good for Flux
    "40GB": "A100",    # High-end
    "80GB": "A100",    # Maximum VRAM (A100-80GB)
    "H100": "H100",    # Fastest
}

def get_gpu_for_template(template: str) -> str:
    """Map template to appropriate GPU based on requirements."""
    # Template-specific GPU requirements
    template_gpus = {
        "boomboom": "L40S",     # Flux Kontext needs 24GB+
        "sd15-basic": "L4",     # SD 1.5 works on 16GB
    }
    return template_gpus.get(template, "L40S")
