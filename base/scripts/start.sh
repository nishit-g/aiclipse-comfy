#!/bin/bash
set -e

# Source logging library
source /scripts/lib/logging.sh

log_info "🚀 Starting AiClipse ComfyUI Template System"

# Environment setup
export TEMPLATE_VERSION="${TEMPLATE_VERSION:-1.0.0}"
export TEMPLATE_TYPE="${TEMPLATE_TYPE:-base}"
log_info "📋 Template Type: $TEMPLATE_TYPE"
export COMFY_DIR="/workspace/aiclipse/ComfyUI"
export VENV_PATH="/venv"
export MODELS_DIR="/workspace/aiclipse/models"
export TEMPLATE_VERSION_FILE="/workspace/aiclipse/template.json"
export CONFIG_REPO="${CONFIG_REPO:-https://github.com/nishit-g/aiclipse-comfy}"
export CONFIG_BRANCH="${CONFIG_BRANCH:-main}"

# Self-update function
update_self() {
    if [ "${AUTO_UPDATE:-true}" != "true" ]; then
        log_info "Skipping auto-update (AUTO_UPDATE=false)"
        return 0
    fi

    log_info "Checking for updates from $CONFIG_REPO..."
    
    local temp_dir=$(mktemp -d)
    
    if git clone --depth 1 -b "$CONFIG_BRANCH" "$CONFIG_REPO" "$temp_dir" >/dev/null 2>&1; then
        # Check if scripts have changed
        if ! diff -r "$temp_dir/base/scripts" "/scripts" >/dev/null 2>&1; then
            log_warn "Updates detected! Applying changes..."
            
            # Update scripts
            rsync -a "$temp_dir/base/scripts/" "/scripts/"
            chmod +x /scripts/*.sh /scripts/*.py
            
            # Update manifests
            if [ -d "$temp_dir/manifests" ]; then
                rsync -a "$temp_dir/manifests/" "/manifests/"
            fi
            
            log_success "Update complete. Reloading..."
            rm -rf "$temp_dir"
            
            # Re-exec self
            exec "$0" "$@"
        else
            log_info "Scripts are up to date."
        fi
    else
        log_error "Failed to check for updates. Continuing with local scripts."
    fi
    
    rm -rf "$temp_dir"
}

# Source all setup modules
source /scripts/setup_symlinks.sh
source /scripts/setup_sync.sh
source /scripts/setup_models.sh
source /scripts/setup_services.sh
source /scripts/setup_nodes.sh

# Main startup sequence
main() {
    # Check for updates first
    update_self

    log_info "🔧 Setting up environment..."
    setup_environment

    log_info "🔐 Configuring SSH access..."
    setup_ssh_with_export

    log_info "🔗 Creating symlinks..."
    setup_symlinks

    log_info "🔄 Checking template sync..."
    sync_template_if_needed

    log_info "📦 Setting up ComfyUI..."
    setup_comfyui

    log_info "🎯 Configuring model paths..."
    setup_model_paths

    log_info "🔌 Installing custom nodes..."
    setup_custom_nodes

    log_info "📥 Starting model downloads..."
    download_models_async

    log_info "🌐 Starting services..."
    start_all_services

    log_info "🎨 Starting ComfyUI..."
    start_comfyui_with_custom_args
}

# Environment setup
setup_environment() {
    # Whitelist specific safe environment variables
    SAFE_VARS=(
        "RUNPOD_POD_ID"
        "RUNPOD_POD_NAME"
        "RUNPOD_API_ENDPOINT"
        "CUDA_VISIBLE_DEVICES"
        "NVIDIA_VISIBLE_DEVICES"
        "LD_LIBRARY_PATH"
        "PATH"
        "PYTHONPATH"
        "TEMPLATE_TYPE"
        "TEMPLATE_VERSION"
        "GPU_TYPE"
    )

    # Create environment file for SSH sessions
    echo "# AiClipse Environment Variables" > /etc/rp_environment
    echo "# Generated at $(date)" >> /etc/rp_environment

    for var in "${SAFE_VARS[@]}"; do
        if [[ -n "${!var}" ]]; then
            # Escape quotes and special characters
            value=$(printf '%q' "${!var}")
            echo "export $var=$value" >> /etc/rp_environment
        fi
    done

    # Source environment in bash sessions
    echo 'source /etc/rp_environment 2>/dev/null || true' >> ~/.bashrc
    echo 'source /etc/rp_environment 2>/dev/null || true' >> /etc/bash.bashrc

    # Set permissions
    chmod 644 /etc/rp_environment
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
        log_success "SSH configured with public key"
    else
        RANDOM_PASS=$(openssl rand -base64 12)
        echo "root:${RANDOM_PASS}" | chpasswd
        log_info "SSH password: ${RANDOM_PASS}"
    fi

    /usr/sbin/sshd
}

# ComfyUI setup
setup_comfyui() {
    if [ ! -d "$COMFY_DIR" ]; then
        log_info "First time setup: Installing ComfyUI..."
        git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
    else
        log_success "ComfyUI already installed"
    fi

    # Always ensure requirements are installed (in case of container restart)
    cd "$COMFY_DIR"
    log_info "Installing/Verifying ComfyUI requirements..."
    /venv/bin/uv pip install --python /venv/bin/python -r requirements.txt
    
    # Explicitly install critical dependencies that might be missing from requirements.txt
    log_info "Installing critical dependencies (einops, aiohttp)..."
    /venv/bin/uv pip install --python /venv/bin/python einops aiohttp

    # Install/Update ComfyUI Manager
    if [ ! -d "custom_nodes/ComfyUI-Manager" ]; then
        log_info "Installing ComfyUI Manager..."
        git clone https://github.com/ltdrdata/ComfyUI-Manager custom_nodes/ComfyUI-Manager
    fi

    # Always ensure Manager requirements are installed
    if [ -f "custom_nodes/ComfyUI-Manager/requirements.txt" ]; then
        log_info "Installing/Verifying ComfyUI Manager requirements..."
        /venv/bin/uv pip install --python /venv/bin/python -r custom_nodes/ComfyUI-Manager/requirements.txt
    fi
}

# Start ComfyUI with custom arguments
start_comfyui_with_custom_args() {
    cd "$COMFY_DIR"

    # Base arguments
    local args="--listen 0.0.0.0 --port 8188"

    # Add SageAttention if enabled
    if [ "$ENABLE_SAGE_ATTENTION" = "true" ]; then
        args="$args --use-sage-attention"
    fi

    if [ -n "$COMFY_ARGS" ]; then
        args="$args $COMFY_ARGS"
        log_info "Using COMFY_ARGS env: $COMFY_ARGS"
    fi

    log_info "Starting ComfyUI with: $args"
    exec /venv/bin/python main.py $args
}

# Run main function
main "$@"
