#!/bin/bash

setup_model_paths() {
    log "🎯 Configuring ComfyUI model paths..."

    # Create extra_model_paths.yaml
    cat > "$COMFY_DIR/extra_model_paths.yaml" << 'YAML'
models:
  checkpoints: /workspace/aiclipse/models/checkpoints
  diffusion_models: /workspace/aiclipse/models/diffusion_models
  vae: /workspace/aiclipse/models/vae
  loras: /workspace/aiclipse/models/loras
  clip: /workspace/aiclipse/models/clip
  controlnet: /workspace/aiclipse/models/controlnet
  upscale_models: /workspace/aiclipse/models/upscale_models
  embeddings: /workspace/aiclipse/models/embeddings
YAML

    log "✅ Model paths configured"
}

download_models_async() {
    local manifest_file="/workspace/aiclipse/models_manifest.txt"

    # Use template-specific manifest if available
    if [ ! -f "$manifest_file" ]; then
        # Try template-specific manifest first
        local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
        if [ -f "$template_manifest" ]; then
            cp "$template_manifest" "$manifest_file"
            log "📋 Created manifest from template: ${TEMPLATE_TYPE}"
        # Fallback to environment variable
        elif [ -n "$MODELS_MANIFEST" ] && [ -f "$MODELS_MANIFEST" ]; then
            cp "$MODELS_MANIFEST" "$manifest_file"
            log "📋 Created manifest from environment: $MODELS_MANIFEST"
        # Fallback to base manifest
        elif [ -f "/manifests/base_models.txt" ]; then
            cp "/manifests/base_models.txt" "$manifest_file"
            log "📋 Created manifest from base models"
        else
            log "ℹ️ No model manifest found - starting with empty model directory"
            return 0
        fi
    fi

    # Start async download if manifest exists and enabled
    if [ -f "$manifest_file" ] && [ "$DOWNLOAD_MODELS" = "true" ]; then
        log "📥 Starting model downloads in background..."

        # Ensure logs directory exists
        mkdir -p /workspace/aiclipse/logs

        # Start download with better error handling
        nohup /venv/bin/python /scripts/download_models.py \
            --manifest "$manifest_file" \
            --models-dir "$MODELS_DIR" \
            > /workspace/aiclipse/logs/models.log 2>&1 &

        local download_pid=$!
        echo $download_pid > /workspace/aiclipse/logs/models.pid

        log "📊 Model download log: /workspace/aiclipse/logs/models.log"
        log "🔢 Model download PID: $download_pid"
    elif [ "$DOWNLOAD_MODELS" != "true" ]; then
        log "⏭️ Model downloads disabled (DOWNLOAD_MODELS=false)"
    else
        log "ℹ️ No models to download"
    fi
}
