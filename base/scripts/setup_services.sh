#!/bin/bash

start_all_services() {
    log "🌐 Starting background services..."

    mkdir -p /workspace/aiclipse/logs

    # Start FileBrowser
    start_filebrowser

    # Start Zasper
    start_zasper

    # Start JupyterLab if enabled
    if [ "${ENABLE_JUPYTER:-true}" = "true" ]; then
        start_jupyter
    fi
}

start_filebrowser() {
    local db_file="/workspace/aiclipse/filebrowser.db"

    if [ ! -f "$db_file" ]; then
        filebrowser config init --database "$db_file"
        filebrowser config set --address 0.0.0.0 --port 8080 --root /workspace --auth.method=noauth --database "$db_file"
        filebrowser users add admin admin --database "$db_file"
    fi

    log "📁 Starting FileBrowser on port 8080..."
    nohup filebrowser --database "$db_file" > /workspace/aiclipse/logs/filebrowser.log 2>&1 &
}

start_zasper() {
    log "📝 Starting Zasper on port 8048..."
    nohup zasper --port 0.0.0.0:8048 --cwd /workspace > /workspace/aiclipse/logs/zasper.log 2>&1 &
}

start_jupyter() {
    log "🪐 Starting JupyterLab on port 8888..."
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
