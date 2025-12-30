# AiClipse ComfyUI Library
# Shared utilities for all templates

from .config import Config, TemplateConfig
from .models import ModelDownloader, BatchDownloadResult
from .paths import setup_model_paths
from .comfy import ComfyLauncher, install_custom_nodes
from .gpu import GPUVariant, get_gpu_config

__version__ = "3.0.0"
__all__ = [
    "Config",
    "TemplateConfig", 
    "ModelDownloader",
    "BatchDownloadResult",
    "setup_model_paths",
    "ComfyLauncher",
    "install_custom_nodes",
    "GPUVariant",
    "get_gpu_config",
]
