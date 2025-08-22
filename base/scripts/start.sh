#!/bin/bash
set -e

echo "🚀 Starting AiClipse ComfyUI Template System"

# Environment setup
export TEMPLATE_VERSION="${TEMPLATE_VERSION:-1.0.0}"
export TEMPLATE_TYPE="${TEMPLATE_TYPE:-base}"
export COMFY_DIR="/workspace/aiclipse/ComfyUI"
export VENV_PATH="/venv"
export MODELS_DIR="/workspace/aiclipse/models"
export TEMPLATE_VERSION_FILE="/workspace/aiclipse/template.json"

# Source all setup modules
source /scripts/setup_symlinks.sh
source /scripts/setup_sync.sh
source /scripts/setup_models.sh
source /scripts/setup_services.sh

# Main startup sequence
main() {
    log "🔧 Setting up environment..."
    setup_environment

    log "🔐 Configuring SSH access..."
    setup_ssh_with_export

    log "🔗 Creating symlinks..."
    setup_symlinks

    log "🔄 Checking template sync..."
    sync_template_if_needed

    log "📦 Setting up ComfyUI..."
    setup_comfyui

    log "🎯 Configuring model paths..."
    setup_model_paths

    log "📥 Starting model downloads..."
    download_models_async

    log "🌐 Starting services..."
    start_all_services

    log "🎨 Starting ComfyUI..."
    start_comfyui_with_custom_args
}

# Logging helper
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# Environment setup
setup_environment() {
    # Export RunPod environment for SSH sessions
    printenv | grep -E '^RUNPOD_|^CUDA|^LD_LIBRARY_PATH|^PATH' | while read -r line; do
        name=$(echo "$line" | cut -d= -f1)
        value=$(echo "$line" | cut -d= -f2-)
        echo "export $name=\"$value\"" >> /etc/rp_environment
    done
    echo 'source /etc/rp_environment' >> ~/.bashrc
    echo 'source /etc/rp_environment' >> /etc/bash.bashrc
}

# SSH setup with environment export
setup_ssh_with_export() {
    mkdir -p ~/.ssh

    # Generate host keys if missing
    for type in rsa ecdsa ed25519; do
        if [ ! -f "/etc/ssh/ssh_host_${type}_key" ]; then
            ssh-keygen -t ${type} -f "/etc/ssh/ssh_host_${type}_key" -q -N ''
        fi
    done

    # Setup authentication
    if [[ $PUBLIC_KEY ]]; then
        echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        log "✅ SSH configured with public key"
    else
        RANDOM_PASS=$(openssl rand -base64 12)
        echo "root:${RANDOM_PASS}" | chpasswd
        log "🔑 SSH password: ${RANDOM_PASS}"
    fi

    /usr/sbin/sshd
}

# ComfyUI setup
setup_comfyui() {
    if [ ! -d "$COMFY_DIR" ]; then
        log "📦 First time setup: Installing ComfyUI..."
        git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
        cd "$COMFY_DIR"

        # Install ComfyUI requirements
        /venv/bin/pip install --no-cache-dir -r requirements.txt

        # Install ComfyUI Manager
        cd custom_nodes
        git clone https://github.com/ltdrdata/ComfyUI-Manager
        if [ -f ComfyUI-Manager/requirements.txt ]; then
            /venv/bin/pip install --no-cache-dir -r ComfyUI-Manager/requirements.txt
        fi

        log "✅ ComfyUI installation complete"
    else
        log "✅ ComfyUI already installed"
    fi
}

# Custom arguments setup
setup_custom_args() {
    local args_file="/workspace/aiclipse/comfyui_args.txt"
    if [ ! -f "$args_file" ]; then
        cat > "$args_file" << 'EOF'
# Custom ComfyUI arguments (one per line)
# --lowvram
# --force-fp16
# --disable-xformers
EOF
    fi
}

# Start ComfyUI with custom arguments
start_comfyui_with_custom_args() {
    cd "$COMFY_DIR"

    setup_custom_args

    # Base arguments
    local args="--listen 0.0.0.0 --port 8188"

    # Add SageAttention if enabled
    if [ "$ENABLE_SAGE_ATTENTION" = "true" ]; then
        args="$args --use-sage-attention"
    fi

    # Add custom arguments
    local custom_args_file="/workspace/aiclipse/comfyui_args.txt"
    if [ -f "$custom_args_file" ]; then
        local custom_args=$(grep -v '^#' "$custom_args_file" | grep -v '^$' | tr '\n' ' ')
        if [ -n "$custom_args" ]; then
            args="$args $custom_args"
            log "📝 Using custom args: $custom_args"
        fi
    fi

    log "🎨 Starting ComfyUI with: $args"
    exec /venv/bin/python main.py $args
}

# Run main function
main "$@"
