"""
AiClipse ComfyUI - Qwen Multi-Edit (RTX 5090 Variant)
Optimized for NVIDIA RTX 5090 with CUDA 12.8 and Blackwell architecture.

Deploy: modal deploy v3/templates/qwen-multi-edit/modal/app_rtx5090.py
"""

import os
os.environ["GPU_VARIANT"] = "rtx5090"

# Import and re-export everything from main app
from app import *

# Override GPU config for RTX 5090
from aiclipse.gpu import get_gpu_config, GPUVariant

GPU = get_gpu_config(GPUVariant.RTX_5090)

# Note: RTX 5090 is not available on Modal cloud
# This variant is for reference/future use
# For cloud deployment, use A10G or A100
