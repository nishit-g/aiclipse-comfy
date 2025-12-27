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
    
    if file_exists "requirements.txt"; then
        "$VENV_PATH/bin/uv" pip install --python "$VENV_PATH/bin/python" -r requirements.txt
    fi
    
    # Critical dependencies
    log_info "Installing critical dependencies..."
    "$VENV_PATH/bin/uv" pip install --python "$VENV_PATH/bin/python" einops aiohttp

    # ComfyUI Manager
    local manager_dir="$COMFY_DIR/custom_nodes/ComfyUI-Manager"
    if [[ ! -d "$manager_dir" ]]; then
        log_info "Installing ComfyUI Manager..."
        git clone https://github.com/ltdrdata/ComfyUI-Manager "$manager_dir"
    fi
    
    if file_exists "$manager_dir/requirements.txt"; then
        "$VENV_PATH/bin/uv" pip install --python "$VENV_PATH/bin/python" -r "$manager_dir/requirements.txt"
    fi
    
    log_success "ComfyUI setup complete"
}

# Run module
setup_comfyui
