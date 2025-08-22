#!/bin/bash

COMFY_DIR=$1
echo "📥 Downloading headshot models..."

mkdir -p "$COMFY_DIR/models"/{checkpoints,loras,controlnet,vae}

# Function to download with resume
download_model() {
    local url=$1
    local path=$2
    local desc=$3

    if [ -f "$path" ]; then
        echo "✅ $desc already exists"
        return 0
    fi

    echo "⬇️ Downloading $desc..."
    wget -c -O "$path.tmp" "$url" && mv "$path.tmp" "$path"
}

# Essential headshot models
download_model \
    "https://civitai.com/api/download/models/130072" \
    "$COMFY_DIR/models/checkpoints/realistic_vision_v5.safetensors" \
    "Realistic Vision V5"

# Custom nodes for headshots
cd "$COMFY_DIR/custom_nodes"
[ ! -d "comfyui-reactor-node" ] && git clone https://github.com/Gourieff/comfyui-reactor-node

echo "🎉 Headshot template ready!"
