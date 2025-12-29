#!/bin/bash
# =============================================================================
# Module 05: ComfyUI Installation
# Clones, installs, and configures ComfyUI
# =============================================================================

setup_comfyui() {
    log_step "Setting up ComfyUI..."
    
    if [[ ! -f "$COMFY_DIR/main.py" ]]; then
        log_info "ComfyUI missing or incomplete. Installing..."
        
        if dir_exists "$COMFY_DIR"; then
            log_warn "Directory exists but main.py missing. Repairing..."
            cd "$COMFY_DIR"
            git init 2>/dev/null || true
            git remote add origin https://github.com/comfyanonymous/ComfyUI.git 2>/dev/null || \
                git remote set-url origin https://github.com/comfyanonymous/ComfyUI.git
            git fetch origin
            git checkout -f master
            git reset --hard origin/master
        else
            git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
        fi
    else
        log_info "ComfyUI already installed"
    fi

    # Install requirements
    cd "$COMFY_DIR"
    log_info "Installing ComfyUI requirements..."
    
    # Note: ComfyUI-Manager is now installed via pip in the base layer (02-comfyui.dockerfile)
    # It's activated via COMFY_ARGS="--enable-manager"
    # No need to clone it as a custom node anymore!
    
    "$VENV_PATH/bin/uv" pip install --quiet --python "$VENV_PATH/bin/python" \
        -r requirements.txt einops aiohttp
    
    log_success "ComfyUI setup complete"
}

# Run module
setup_comfyui
