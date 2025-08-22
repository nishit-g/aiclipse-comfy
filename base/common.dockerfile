ARG CUDA_VERSION=12.8
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg
ENV PATH="/venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    git python3.12 python3.12-venv python3.12-dev \
    build-essential wget curl htop tmux nano vim \
    openssh-server nginx ca-certificates \
    ffmpeg jq aria2 rsync inotify-tools \
    software-properties-common gpg-agent \
    && rm -rf /var/lib/apt/lists/*

# Install modern tools
RUN curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
RUN wget https://github.com/zasper-io/zasper/releases/download/v0.1.0-alpha/zasper-webapp-linux-amd64.tar.gz && \
    tar xf zasper-webapp-linux-amd64.tar.gz -C /usr/local/bin && \
    rm zasper-webapp-linux-amd64.tar.gz

# Python setup
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --set python3 /usr/bin/python3.12 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    pip install --no-cache-dir jupyterlab uv

# SSH configuration for RunPod
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PermitUserEnvironment yes" >> /etc/ssh/sshd_config && \
    mkdir -p /run/sshd

# Create workspace structure
RUN mkdir -p /workspace/aiclipse/{ComfyUI,models,workflows,output,logs,temp} && \
    mkdir -p /workspace/aiclipse/models/{checkpoints,diffusion_models,vae,loras,clip,controlnet,upscale_models,embeddings}

WORKDIR /workspace/aiclipse
