"""
Modal Volume Configuration
==========================
Defines persistent storage for models, outputs, and workflows.
"""
import modal

# =============================================================================
# Volume Definitions (Volumes v2 for better performance)
# =============================================================================

# Models Volume: Pre-downloaded checkpoints, VAEs, LoRAs, etc.
# Populated by CPU download function, read by GPU server
models_volume = modal.Volume.from_name(
    "aiclipse-models", 
    create_if_missing=True,
)

# Outputs Volume: Generated images, videos
outputs_volume = modal.Volume.from_name(
    "aiclipse-outputs",
    create_if_missing=True,
)

# Workflows Volume: User-saved workflows (persist across deploys)
workflows_volume = modal.Volume.from_name(
    "aiclipse-workflows",
    create_if_missing=True,
)

# =============================================================================
# Mount Paths (inside container)
# =============================================================================

MODELS_PATH = "/modal-volumes/models"
OUTPUTS_PATH = "/modal-volumes/outputs"
WORKFLOWS_PATH = "/modal-volumes/workflows"

def get_volume_mounts():
    """Return volume mount configuration for ComfyUI server."""
    return {
        MODELS_PATH: models_volume,
        OUTPUTS_PATH: outputs_volume,
        WORKFLOWS_PATH: workflows_volume,
    }

def get_download_volume_mounts():
    """Return volume mounts for download function (models only)."""
    return {
        MODELS_PATH: models_volume,
    }
