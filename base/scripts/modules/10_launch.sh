#!/bin/bash
# =============================================================================
# Module 10: Launch ComfyUI
# Final module - starts ComfyUI with configured arguments
# =============================================================================

launch_comfyui() {
    log_section "🎨 Starting ComfyUI"
    
    cd "$COMFY_DIR"

    # Base arguments
    local args="--listen 0.0.0.0 --port 8188"

    # Add COMFY_ARGS if set
    if [[ -n "${COMFY_ARGS:-}" ]]; then
        args="$args $COMFY_ARGS"
        log_info "Using COMFY_ARGS: $COMFY_ARGS"
    elif is_true "${ENABLE_SAGE_ATTENTION:-false}"; then
        args="$args --use-sage-attention"
    fi
    
    # Try to load from config.yaml if available
    local config="/templates/${TEMPLATE_TYPE}/config.yaml"
    if file_exists "$config"; then
        local yaml_args
        yaml_args=$(yaml_list "$config" "comfy_args" 2>/dev/null | tr '\n' ' ' | sed 's/"//g')
        if [[ -n "$yaml_args" ]]; then
            args="$args $yaml_args"
            log_info "Added args from config.yaml"
        fi
    fi

    log_info "Launch command: python main.py $args"
    log_success "ComfyUI is starting..."
    
    # Replace process with ComfyUI
    exec "$VENV_PATH/bin/python" main.py $args
}

# Run module
launch_comfyui
