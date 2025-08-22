FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Install essential tools for RunPod
RUN apt-get update && apt-get install -y \
    openssh-server nginx rsync wget git curl \
    build-essential software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install FileBrowser for file management
RUN curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash

# Install modern Python package managers
RUN pip install jupyterlab uv

# ComfyUI setup
WORKDIR /ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip install -r requirements.txt

# Environment variables
ENV PUBLIC_KEY=""
ENV JUPYTER_TOKEN=""
ENV DOWNLOAD_MODELS=true

# Scripts
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22 8188 8888
CMD ["/start.sh"]
