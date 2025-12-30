# AiClipse ComfyUI - Qwen Multi-Edit (RunPod)
# Multi-stage Dockerfile with GPU variant support
#
# Build examples:
#   docker build --build-arg GPU_VARIANT=rtx4090 -t comfy-qwen:rtx4090 .
#   docker build --build-arg GPU_VARIANT=rtx5090 -t comfy-qwen:rtx5090 .
#   docker build --build-arg GPU_VARIANT=a100 -t comfy-qwen:a100 .

# =============================================================================
# Build Arguments
# =============================================================================
ARG GPU_VARIANT=rtx4090

# =============================================================================
# GPU Variant Configuration
# =============================================================================
# RTX 4090: CUDA 12.4, Ada Lovelace (highest consumer performance)
# RTX 5090: CUDA 12.8, Blackwell (future)
# A10G:     CUDA 12.4, Ampere (cloud gaming GPU)
# A100:     CUDA 12.4, Ampere (datacenter, best for large models)
# H100:     CUDA 12.4, Hopper (highest datacenter performance)

# =============================================================================
# Layer 1: Base Image Selection (GPU-specific)
# =============================================================================
FROM runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04 AS base-rtx4090
FROM runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04 AS base-rtx5090
FROM runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04 AS base-a10g
FROM runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04 AS base-a100
FROM runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04 AS base-h100

# Select base based on GPU_VARIANT
FROM base-${GPU_VARIANT} AS base

# Set GPU-specific environment
ARG GPU_VARIANT
ENV GPU_VARIANT=${GPU_VARIANT}

# =============================================================================
# Layer 2: System Dependencies (CACHED LONG)
# =============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core tools
    git git-lfs wget curl \
    # Video/Image processing (for ComfyUI)
    ffmpeg libgl1 libglib2.0-0 \
    # Fast parallel downloads
    aria2 \
    # SSH access (RunPod feature)
    openssh-server \
    # Debug tools
    htop nano tmux \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd

# =============================================================================
# Layer 3: Python Dependencies (CACHED MEDIUM)
# =============================================================================
RUN pip install --no-cache-dir \
    # ComfyUI CLI
    "comfy-cli>=1.0.0" \
    # Model downloads
    huggingface-hub \
    boto3 \
    # Config
    pyyaml \
    safetensors

# =============================================================================
# Layer 4: ComfyUI Installation (CACHED MEDIUM)
# =============================================================================
# CUDA version based on GPU variant
ARG GPU_VARIANT
RUN CUDA_VER=$(case ${GPU_VARIANT} in \
    rtx5090) echo "12.8" ;; \
    *) echo "12.4" ;; \
    esac) && \
    comfy --skip-prompt install --nvidia --cuda-version ${CUDA_VER}

# =============================================================================
# Layer 5: AiClipse Library (CHANGES OFTEN)
# =============================================================================
WORKDIR /app

# Copy shared library
COPY v3/shared/aiclipse /app/aiclipse

# Copy template config
COPY v3/templates/qwen-multi-edit/config.yaml /app/config.yaml

# Copy workflows to ComfyUI
COPY v3/templates/qwen-multi-edit/workflows /root/comfy/user/default/workflows

# Copy entrypoint
COPY v3/templates/qwen-multi-edit/runpod/entrypoint.py /app/entrypoint.py

# =============================================================================
# Environment Variables
# =============================================================================
ENV PYTHONPATH=/app
ENV TEMPLATE_NAME=qwen-multi-edit
ENV MODELS_PATH=/runpod-volume/models
ENV OUTPUTS_PATH=/runpod-volume/outputs
ENV COMFY_PATH=/root/comfy

# User-configurable at runtime:
# ENV COMFY_ARGS="--preview-method auto --fast"
# ENV SKIP_MODEL_DOWNLOAD=true
# ENV HF_TOKEN=your_token
# ENV PUBLIC_KEY="ssh-rsa ..."
# ENV ENABLE_JUPYTER=true

# Expose ports
# 8188 = ComfyUI
# 22 = SSH
# 8888 = JupyterLab (optional)
EXPOSE 8188 22 8888

# =============================================================================
# Entrypoint
# =============================================================================
CMD ["python", "/app/entrypoint.py"]
