"""
AiClipse ComfyUI on Modal - Main Entry Point
=============================================

Enterprise-level deployment with:
- CPU-based model downloads (cheap)
- GPU-based ComfyUI server (fast)
- Pre-downloaded models in Volumes (instant cold starts)
- Memory snapshots (even faster restarts)
- Multi-template support

Usage:
    # First, download models (CPU, cheap)
    modal run platform/modal/download.py --template boomboom
    
    # Then, deploy ComfyUI server (GPU)
    modal deploy platform/modal/app.py
    
    # Or dev mode with hot reload
    modal serve platform/modal/app.py
"""
import modal

# Re-export from submodules
from .serve import app, ComfyUI
from .download import download_models_for_template

# Make this the main app
__all__ = ["app", "ComfyUI", "download_models_for_template"]
