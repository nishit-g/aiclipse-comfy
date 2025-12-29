ARG CUDA_VERSION=12.4.1
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu22.04

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    PATH="/venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache && \
    apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    software-properties-common gpg-agent \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && \
    apt-get install -y --no-install-recommends \
    git python3.12 python3.12-venv python3.12-dev \
    build-essential wget curl htop tmux nano vim \
    openssh-server nginx ca-certificates \
    ffmpeg jq aria2 rsync inotify-tools

# Python setup with base virtual environment
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --set python3 /usr/bin/python3.12

# Create virtual environment and install ALL Python packages
# Consolidated for better caching and fewer layers

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /venv --python python3.12 && \
    uv pip install --no-cache-dir \
    jupyterlab \
    huggingface-hub \
    safetensors \
    accelerate \
    requests[security] \
    tqdm \
    boto3 \
    botocore \
    urllib3

# SSH configuration for RunPod
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PermitUserEnvironment yes" >> /etc/ssh/sshd_config && \
    mkdir -p /run/sshd

# Create workspace structure (minimal - ComfyUI creates its own models/ subdirs)
# NOTE: Model directories are NOT needed here because:
#   1. ComfyUI automatically creates models/checkpoints, models/loras, etc. on startup
#   2. extra_model_paths.yaml points ComfyUI to external model locations (Modal Volume)
#   3. The 02-comfyui.dockerfile clones ComfyUI which already has a models/ dir
RUN mkdir -p /workspace/aiclipse/logs /workspace/aiclipse/temp

# COMMENTED OUT: Redundant model directory creation
# These were causing issues with extra_model_paths.yaml and symlinks
# RUN mkdir -p /workspace/aiclipse/ComfyUI \
#     /workspace/aiclipse/models \
#     /workspace/aiclipse/workflows \
#     /workspace/aiclipse/output \
#     /workspace/aiclipse/logs \
#     /workspace/aiclipse/temp && \
#     mkdir -p /workspace/aiclipse/models/checkpoints \
#     /workspace/aiclipse/models/diffusion_models \
#     /workspace/aiclipse/models/vae \
#     /workspace/aiclipse/models/loras \
#     /workspace/aiclipse/models/clip \
#     /workspace/aiclipse/models/controlnet \
#     /workspace/aiclipse/models/upscale_models \
#     /workspace/aiclipse/models/embeddings \
#     /workspace/aiclipse/models/text_encoders \
#     /workspace/aiclipse/models/unet

# Set default environment variables
ENV DOWNLOAD_MODELS=true
ENV VERIFY_CHECKSUMS=true
ENV AUTO_RETRY_FAILED=3
ENV CIVITAI_RATE_LIMIT=10
ENV CIVITAI_DOWNLOAD_TIMEOUT=3000

WORKDIR /workspace/aiclipse

# --- VOLATILE LAYERS BELOW ---
# We copy scripts and manifests LAST so that changing them
# does NOT invalidate the heavy Python installation layer.

# Copy manifests directory
COPY manifests/ /manifests/

# Copy enhanced scripts
COPY base/scripts/ /scripts/
RUN chmod +x /scripts/*.sh /scripts/*.py
# Trigger build
# Force full rebuild
