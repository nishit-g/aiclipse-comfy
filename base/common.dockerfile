ARG CUDA_VERSION=12.4.1
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg
ENV PATH="/venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    software-properties-common gpg-agent \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && \
    apt-get install -y --no-install-recommends \
    git python3.12 python3.12-venv python3.12-dev \
    build-essential wget curl htop tmux nano vim \
    openssh-server nginx ca-certificates \
    ffmpeg jq aria2 rsync inotify-tools \
    && rm -rf /var/lib/apt/lists/*

# Python setup with base virtual environment
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --set python3 /usr/bin/python3.12 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Create virtual environment and install ALL Python packages
# Consolidated for better caching and fewer layers
RUN python3.12 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip wheel setuptools && \
    /venv/bin/pip install --no-cache-dir \
    jupyterlab \
    uv \
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

# Create workspace structure
RUN mkdir -p /workspace/aiclipse/{ComfyUI,models,workflows,output,logs,temp} && \
    mkdir -p /workspace/aiclipse/models/{checkpoints,diffusion_models,vae,loras,clip,controlnet,upscale_models,embeddings}

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
