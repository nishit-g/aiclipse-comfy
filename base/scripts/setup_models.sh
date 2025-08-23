#!/bin/bash
# Enhanced Model Setup Script with R2 and CivitAI support

setup_model_paths() {
    log "🎯 Configuring ComfyUI model paths..."

    # Create extra_model_paths.yaml with enhanced structure
    cat > "$COMFY_DIR/extra_model_paths.yaml" << 'YAML'
models:
  checkpoints: /workspace/aiclipse/models/checkpoints
  diffusion_models: /workspace/aiclipse/models/diffusion_models
  text_encoders: /workspace/aiclipse/models/text_encoders
  unet: /workspace/aiclipse/models/unet
  vae: /workspace/aiclipse/models/vae
  loras: /workspace/aiclipse/models/loras
  clip: /workspace/aiclipse/models/clip
  controlnet: /workspace/aiclipse/models/controlnet
  upscale_models: /workspace/aiclipse/models/upscale_models
  embeddings: /workspace/aiclipse/models/embeddings
  hypernetworks: /workspace/aiclipse/models/hypernetworks
  t2i_adapter: /workspace/aiclipse/models/t2i_adapter
  clip_vision: /workspace/aiclipse/models/clip_vision
  style_models: /workspace/aiclipse/models/style_models
  photomaker: /workspace/aiclipse/models/photomaker
YAML

    log "✅ Enhanced model paths configured"
}

check_enhanced_dependencies() {
    log "🔍 Checking enhanced downloader dependencies..."

    # Check for boto3 (R2 support)
    if ! /venv/bin/python -c "import boto3" 2>/dev/null; then
        log "📦 Installing boto3 for R2 support..."
        /venv/bin/pip install --no-cache-dir boto3 botocore
    else
        log "✅ boto3 available for R2 support"
    fi

    # Check for requests with security features
    if ! /venv/bin/python -c "import requests; import urllib3" 2>/dev/null; then
        log "📦 Installing enhanced requests..."
        /venv/bin/pip install --no-cache-dir "requests[security]" urllib3
    else
        log "✅ Enhanced requests available"
    fi

    log "✅ All dependencies available"
}

validate_credentials() {
    log "🔐 Validating download credentials..."

    local has_credentials=false

    # Check HuggingFace token
    if [ -n "$HF_TOKEN" ]; then
        log "✅ HuggingFace token configured"
        has_credentials=true
    else
        log "ℹ️ No HuggingFace token (public models only)"
    fi

    # Check CivitAI token
    if [ -n "$CIVITAI_TOKEN" ] || [ -n "$CIVITAI_API_KEY" ]; then
        log "✅ CivitAI token configured"
        has_credentials=true
    else
        log "ℹ️ No CivitAI token (public models only, may hit rate limits)"
    fi

    # Check R2 credentials
    if [ -n "$R2_ACCESS_KEY_ID" ] && [ -n "$R2_SECRET_ACCESS_KEY" ] && [ -n "$R2_ACCOUNT_ID" ]; then
        log "✅ Cloudflare R2 credentials configured"
        if [ -n "$R2_BUCKET" ]; then
            log "✅ Default R2 bucket: $R2_BUCKET"
        fi
        has_credentials=true
    else
        log "ℹ️ No R2 credentials (R2 models will be skipped)"
    fi

    if [ "$has_credentials" = false ]; then
        log "⚠️ No enhanced credentials configured - only public HuggingFace models available"
    fi
}

test_connections() {
    log "🌐 Testing download service connections..."

    # Test HuggingFace
    if timeout 10 curl -s "https://huggingface.co" > /dev/null; then
        log "✅ HuggingFace Hub accessible"
    else
        log "⚠️ HuggingFace Hub connection issue"
    fi

    # Test CivitAI
    if timeout 10 curl -s "https://civitai.com/api/v1/models" > /dev/null; then
        log "✅ CivitAI API accessible"
    else
        log "⚠️ CivitAI API connection issue"
    fi

    # Test R2 if configured
    if [ -n "$R2_ACCESS_KEY_ID" ] && [ -n "$R2_SECRET_ACCESS_KEY" ] && [ -n "$R2_ACCOUNT_ID" ]; then
        if timeout 10 curl -s "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" > /dev/null; then
            log "✅ Cloudflare R2 accessible"
        else
            log "⚠️ Cloudflare R2 connection issue"
        fi
    fi
}

setup_manifest() {
    local manifest_file="/workspace/aiclipse/models_manifest.txt"

    # Use template-specific manifest if available
    if [ ! -f "$manifest_file" ]; then
        # Try template-specific manifest first
        local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
        if [ -f "$template_manifest" ]; then
            cp "$template_manifest" "$manifest_file"
            log "📋 Using template manifest: ${TEMPLATE_TYPE}"
        # Fallback to environment variable
        elif [ -n "$MODELS_MANIFEST" ] && [ -f "$MODELS_MANIFEST" ]; then
            cp "$MODELS_MANIFEST" "$manifest_file"
            log "📋 Using environment manifest: $MODELS_MANIFEST"
        # Fallback to base manifest
        elif [ -f "/manifests/base_models.txt" ]; then
            cp "/manifests/base_models.txt" "$manifest_file"
            log "📋 Using base models manifest"
        else
            log "ℹ️ No model manifest found - will start with empty models directory"
            return 0
        fi
    else
        log "📋 Using existing manifest: $manifest_file"
    fi

    # Validate manifest before proceeding
    log "🔍 Validating manifest syntax..."
    if /venv/bin/python /scripts/download_models.py \
        --manifest "$manifest_file" \
        --models-dir "$MODELS_DIR" \
        --validate-only; then
        log "✅ Manifest validation passed"
    else
        log_error "❌ Manifest validation failed - check syntax"
        return 1
    fi

    return 0
}

download_models_enhanced() {
    local manifest_file="/workspace/aiclipse/models_manifest.txt"

    # Skip if downloads disabled
    if [ "$DOWNLOAD_MODELS" != "true" ]; then
        log "⭐ Model downloads disabled (DOWNLOAD_MODELS=false)"
        return 0
    fi

    # Skip if no manifest
    if [ ! -f "$manifest_file" ]; then
        log "ℹ️ No models to download"
        return 0
    fi

    # Setup manifest and validate
    if ! setup_manifest; then
        return 1
    fi

    # Check dependencies
    check_enhanced_dependencies

    # Validate credentials
    validate_credentials

    # Test connections
    test_connections

    log "🔥 Starting enhanced model downloads..."

    # Ensure logs directory exists
    mkdir -p /workspace/aiclipse/logs

    # Start enhanced download with better error handling and logging
    if [ "$DOWNLOAD_IN_FOREGROUND" = "true" ]; then
        # Foreground download (for debugging)
        log "🔄 Downloading models in foreground..."
        /venv/bin/python /scripts/download_models.py \
            --manifest "$manifest_file" \
            --models-dir "$MODELS_DIR" \
            2>&1 | tee /workspace/aiclipse/logs/models.log

        local exit_code=${PIPESTATUS[0]}
        if [ $exit_code -eq 0 ]; then
            log "✅ All models downloaded successfully"
        else
            log_error "❌ Some model downloads failed (exit code: $exit_code)"
        fi

    else
        # Background download (default)
        log "🔄 Starting model downloads in background..."
        nohup /venv/bin/python /scripts/download_models.py \
            --manifest "$manifest_file" \
            --models-dir "$MODELS_DIR" \
            > /workspace/aiclipse/logs/models.log 2>&1 &

        local download_pid=$!
        echo $download_pid > /workspace/aiclipse/logs/models.pid

        log "📊 Download progress: tail -f /workspace/aiclipse/logs/models.log"
        log "🔢 Download PID: $download_pid"

        # Show initial progress
        sleep 2
        if ps -p $download_pid > /dev/null; then
            log "✅ Model download process started successfully"
            # Show first few lines of log
            if [ -f /workspace/aiclipse/logs/models.log ]; then
                tail -n 5 /workspace/aiclipse/logs/models.log 2>/dev/null || true
            fi
        else
            log_error "❌ Model download process failed to start"
            if [ -f /workspace/aiclipse/logs/models.log ]; then
                log_error "Last log entries:"
                tail -n 10 /workspace/aiclipse/logs/models.log 2>/dev/null || true
            fi
        fi
    fi
}

monitor_downloads() {
    log "📡 Setting up download monitoring..."

    # Create monitoring script
    cat > /scripts/monitor_downloads.sh << 'EOF'
#!/bin/bash
# Download monitoring helper

PID_FILE="/workspace/aiclipse/logs/models.pid"
LOG_FILE="/workspace/aiclipse/logs/models.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Download process $PID is running"
        echo "📊 Recent progress:"
        tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No logs yet"
    else
        echo "⚠️ Download process completed or failed"
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Final status:"
            grep -E "(success|error|complete)" "$LOG_FILE" | tail -n 3
        fi
        rm -f "$PID_FILE"
    fi
else
    echo "ℹ️ No active download process"
fi
EOF

    chmod +x /scripts/monitor_downloads.sh

    # Create download status command
    cat > /scripts/download_status.sh << 'EOF'
#!/bin/bash
# Quick download status check

LOG_FILE="/workspace/aiclipse/logs/models.log"

if [ -f "$LOG_FILE" ]; then
    echo "📊 Download Summary:"
    grep -c "Downloaded:" "$LOG_FILE" 2>/dev/null | xargs -I {} echo "✅ Successfully downloaded: {} files"
    grep -c "ERROR" "$LOG_FILE" 2>/dev/null | xargs -I {} echo "❌ Failed downloads: {} files"
    grep -c "Skipping" "$LOG_FILE" 2>/dev/null | xargs -I {} echo "⭐ Skipped (existing): {} files"

    echo ""
    echo "🌐 Sources used:"
    grep -o "Downloading.*from [A-Z]*" "$LOG_FILE" 2>/dev/null | sed 's/.*from //' | sort | uniq -c

    echo ""
    echo "📝 Recent activity (last 3 lines):"
    tail -n 3 "$LOG_FILE" 2>/dev/null || echo "No recent activity"
else
    echo "ℹ️ No download logs found"
fi
EOF

    chmod +x /scripts/download_status.sh

    log "✅ Download monitoring tools installed"
    log "🔧 Use: /scripts/monitor_downloads.sh"
    log "🔧 Use: /scripts/download_status.sh"
}

# Main enhanced model setup function
download_models_async() {
    log "🚀 Enhanced model management system starting..."

    # Setup monitoring tools
    monitor_downloads

    # Run enhanced download
    download_models_enhanced

    log "🎯 Enhanced model setup complete"
    log ""
    log "📖 Quick commands:"
    log "  Monitor: /scripts/monitor_downloads.sh"
    log "  Status:  /scripts/download_status.sh"
    log "  Logs:    tail -f /workspace/aiclipse/logs/models.log"
    log ""
}
