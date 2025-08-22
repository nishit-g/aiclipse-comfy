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

    # Use template-specific manifest if available, otherwise no default models
    if [ ! -f "$manifest_file" ]; then
        if [ -f "/manifests/${TEMPLATE_TYPE}_models.txt" ]; then
            cp "/manifests/${TEMPLATE_TYPE}_models.txt" "$manifest_file"
            log "📋 Created manifest from template: ${TEMPLATE_TYPE}"
        else
            log "ℹ️ No model manifest found - starting with empty model directory"
            return 0
        fi
    fi

    # Start async download if manifest exists and enabled
    if [ -f "$manifest_file" ] && [ "$DOWNLOAD_MODELS" = "true" ]; then
        log "📥 Starting model downloads in background..."
        nohup /venv/bin/python /scripts/download_models.py \
            --manifest "$manifest_file" \
            --models-dir "$MODELS_DIR" \
            > /workspace/aiclipse/logs/models.log 2>&1 &

        log "📊 Model download log: /workspace/aiclipse/logs/models.log"
    fi
}
