#!/bin/bash
# =============================================================================
# Module 01: Environment Setup
# Configures environment variables and creates necessary directories
# =============================================================================

setup_environment() {
    log_step "Setting up environment..."
    
    # Create core directories
    ensure_dir "$WORKSPACE"
    ensure_dir "$MODELS_DIR"
    ensure_dir "$LOGS_DIR"
    ensure_dir "$WORKFLOWS_DIR"
    
    # Whitelisted environment variables for SSH sessions
    local SAFE_VARS=(
        "RUNPOD_POD_ID"
        "RUNPOD_POD_NAME"
        "CUDA_VISIBLE_DEVICES"
        "NVIDIA_VISIBLE_DEVICES"
        "LD_LIBRARY_PATH"
        "PATH"
        "PYTHONPATH"
        "TEMPLATE_TYPE"
        "TEMPLATE_VERSION"
        "GPU_TYPE"
        "COMFY_ARGS"
    )

    # Create environment file for SSH sessions
    local env_file="/etc/rp_environment"
    {
        echo "# AiClipse Environment Variables"
        echo "# Generated at $(date)"
        
        for var in "${SAFE_VARS[@]}"; do
            if [[ -n "${!var:-}" ]]; then
                # Escape quotes and special characters
                local value
                value=$(printf '%q' "${!var}")
                echo "export $var=$value"
            fi
        done
    } > "$env_file"

    # Source environment in bash sessions
    if ! grep -q "rp_environment" ~/.bashrc 2>/dev/null; then
        echo 'source /etc/rp_environment 2>/dev/null || true' >> ~/.bashrc
    fi

    chmod 644 "$env_file"
    
    log_success "Environment configured"
}

# Run module
setup_environment
