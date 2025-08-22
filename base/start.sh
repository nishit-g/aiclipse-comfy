#!/bin/bash

echo "🚀 Starting AiClipse ComfyUI Template..."

# SSH setup
if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    service ssh start
    echo "✅ SSH enabled"
fi

# FileBrowser setup
echo "📁 Starting FileBrowser on port 8080..."
if [ ! -f /workspace/aiclipse/filebrowser.db ]; then
    mkdir -p /workspace/aiclipse
    filebrowser config init --database /workspace/aiclipse/filebrowser.db
    filebrowser users add admin admin --database /workspace/aiclipse/filebrowser.db
fi
filebrowser --database /workspace/aiclipse/filebrowser.db --root /workspace --address 0.0.0.0 --port 8080 --noauth &

# ComfyUI setup
COMFY_DIR="/workspace/aiclipse/ComfyUI"

if [ ! -d "$COMFY_DIR" ]; then
    echo "🔧 First time setup: Installing ComfyUI..."
    cd /workspace/aiclipse

    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI

    python -m venv .venv
    source .venv/bin/activate

    pip install uv
    uv pip install -r requirements.txt
    uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

    # Essential custom nodes
    cd custom_nodes
    git clone https://github.com/ltdrdata/ComfyUI-Manager
    git clone https://github.com/crystian/ComfyUI-Crystools

    echo "✅ ComfyUI installation complete"
fi

# Download models if needed
if [ "$DOWNLOAD_MODELS" = "true" ] && [ -n "$TEMPLATE_TYPE" ] && [ -f "/download_models.sh" ]; then
    echo "⬇️ Downloading models for $TEMPLATE_TYPE..."
    bash /download_models.sh "$COMFY_DIR"
fi

# Start ComfyUI
cd "$COMFY_DIR"
source .venv/bin/activate
echo "🎨 Starting ComfyUI..."
python main.py --listen 0.0.0.0 --port 8188
