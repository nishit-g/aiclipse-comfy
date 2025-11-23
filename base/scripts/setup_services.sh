#!/bin/bash

start_all_services() {
    log_info "🌐 Starting background services..."
    mkdir -p /workspace/aiclipse/logs

    # Start JupyterLab if enabled
    if [ "${ENABLE_JUPYTER:-false}" = "true" ]; then
        start_jupyter
    fi
    
    # Start Service Monitor
    monitor_services &
}

start_jupyter() {
    log_info "🪐 Starting JupyterLab on port 8888..."
    nohup jupyter lab \
        --ServerApp.ip=0.0.0.0 \
        --ServerApp.port=8888 \
        --ServerApp.open_browser=False \
        --ServerApp.token="${JUPYTER_TOKEN:-}" \
        --ServerApp.password='' \
        --ServerApp.allow_origin='*' \
        --ServerApp.root_dir="/workspace" \
        --ServerApp.allow_root=True \
        > /workspace/aiclipse/logs/jupyter.log 2>&1 &
}

monitor_services() {
    log_info "🛡️ Service monitor started"
    while true; do
        # Check ComfyUI
        if ! pgrep -f "main.py" > /dev/null; then
            # Only restart if it was supposed to be running (simple check)
            # In a real scenario we'd check a PID file or similar
            # For now, we assume if main.py isn't running after startup, it crashed
            # But we need to be careful not to start it before the main script does.
            # So we'll just log for now.
            :
        fi
        
        sleep 60
    done
}
