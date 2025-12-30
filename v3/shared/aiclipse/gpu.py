"""
GPU Variant Configuration for different hardware targets.

Supports:
- RTX 4090 (CUDA 12.4, consumer)
- RTX 5090 (CUDA 12.8, consumer - Blackwell)
- A10G (CUDA 12.4, Modal cloud)
- A100 (CUDA 12.4, enterprise cloud)
- H100 (CUDA 12.4, enterprise cloud)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GPUVariant(Enum):
    """Supported GPU variants."""
    RTX_4090 = "rtx4090"
    RTX_5090 = "rtx5090"
    A10G = "a10g"
    A100 = "a100"
    H100 = "h100"


@dataclass
class GPUConfig:
    """Configuration for a specific GPU variant."""
    variant: GPUVariant
    cuda_version: str
    pytorch_version: str
    vram_gb: int
    compute_capability: str
    
    # Optimization flags
    supports_fp8: bool = False
    supports_sage_attention: bool = False
    supports_flash_attention: bool = True
    
    # Modal GPU string
    modal_gpu: str = "any"
    
    # Docker base image
    docker_base: str = ""
    
    def get_comfy_args(self) -> list[str]:
        """Get optimized ComfyUI args for this GPU."""
        args = []
        
        if self.supports_fp8:
            args.append("--fast fp8_matrix_mult")
        
        if self.supports_sage_attention:
            args.append("--use-sage-attention")
        
        args.append("--fast autotune")
        
        if self.vram_gb >= 24:
            args.append("--highvram")
        elif self.vram_gb >= 16:
            args.append("--normalvram")
        else:
            args.append("--lowvram")
        
        return args


# GPU Configuration Registry
GPU_CONFIGS: dict[GPUVariant, GPUConfig] = {
    GPUVariant.RTX_4090: GPUConfig(
        variant=GPUVariant.RTX_4090,
        cuda_version="12.4",
        pytorch_version="2.4.0",
        vram_gb=24,
        compute_capability="8.9",
        supports_fp8=True,
        supports_sage_attention=True,
        modal_gpu="any",  # Not typically on Modal
        docker_base="runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04",
    ),
    GPUVariant.RTX_5090: GPUConfig(
        variant=GPUVariant.RTX_5090,
        cuda_version="12.8",
        pytorch_version="2.8.0",
        vram_gb=32,
        compute_capability="10.0",  # Blackwell
        supports_fp8=True,
        supports_sage_attention=True,
        modal_gpu="any",  # Not typically on Modal
        docker_base="nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04",
    ),
    GPUVariant.A10G: GPUConfig(
        variant=GPUVariant.A10G,
        cuda_version="12.4",
        pytorch_version="2.4.0",
        vram_gb=24,
        compute_capability="8.6",
        supports_fp8=True,
        supports_sage_attention=True,
        modal_gpu="A10G",
        docker_base="",  # Uses Modal image builder
    ),
    GPUVariant.A100: GPUConfig(
        variant=GPUVariant.A100,
        cuda_version="12.4",
        pytorch_version="2.4.0",
        vram_gb=80,
        compute_capability="8.0",
        supports_fp8=True,
        supports_sage_attention=True,
        supports_flash_attention=True,
        modal_gpu="A100",
        docker_base="",
    ),
    GPUVariant.H100: GPUConfig(
        variant=GPUVariant.H100,
        cuda_version="12.4",
        pytorch_version="2.4.0",
        vram_gb=80,
        compute_capability="9.0",
        supports_fp8=True,
        supports_sage_attention=True,
        supports_flash_attention=True,
        modal_gpu="H100",
        docker_base="",
    ),
}


def get_gpu_config(variant: str | GPUVariant) -> GPUConfig:
    """Get GPU configuration by variant name or enum."""
    if isinstance(variant, str):
        # Handle string input
        variant_map = {v.value: v for v in GPUVariant}
        if variant.lower() not in variant_map:
            raise ValueError(f"Unknown GPU variant: {variant}. Supported: {list(variant_map.keys())}")
        variant = variant_map[variant.lower()]
    
    return GPU_CONFIGS[variant]


def get_default_gpu_for_platform(platform: str) -> GPUConfig:
    """Get default GPU config for a platform."""
    defaults = {
        "modal": GPUVariant.A10G,
        "runpod": GPUVariant.RTX_4090,
        "local": GPUVariant.RTX_4090,
    }
    variant = defaults.get(platform.lower(), GPUVariant.A10G)
    return GPU_CONFIGS[variant]
