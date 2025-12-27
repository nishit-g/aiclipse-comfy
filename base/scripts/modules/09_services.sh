#!/bin/bash
# =============================================================================
# Module 09: Services
# Starts background services (JupyterLab, monitoring)
# =============================================================================

start_services() {
    log_step "Starting background services..."
    
    ensure_dir "$LOGS_DIR"

    # JupyterLab
    if is_true "${ENABLE_JUPYTER:-false}"; then
        start_jupyter
    fi
    
    # Service monitor (background)
    start_monitor &
}

start_jupyter() {
    log_info "Starting JupyterLab on port 8888..."
    
    nohup jupyter lab \
        --ServerApp.ip=0.0.0.0 \
        --ServerApp.port=8888 \
        --ServerApp.open_browser=False \
        --ServerApp.token="${JUPYTER_TOKEN:-}" \
        --ServerApp.password='' \
        --ServerApp.allow_origin='*' \
        --ServerApp.root_dir="/workspace" \
        --ServerApp.allow_root=True \
        > "$LOGS_DIR/jupyter.log" 2>&1 &
    
    log_success "JupyterLab started"
}

start_monitor() {
    log_debug "Service monitor started"
    
    while true; do
        # Simple health check - restart ComfyUI if crashed
        # For now, just log status
        sleep 60
    done
}

# Run module
start_services
