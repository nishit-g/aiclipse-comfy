#!/bin/bash
# Enhanced Model Setup Script with Aria2c Parallel Downloads

setup_model_paths() {
    log_info "Configuring ComfyUI model paths..."

    # Create extra_model_paths.yaml with enhanced structure
    cat > "$COMFY_DIR/extra_model_paths.yaml" << 'YAML'
comfyui:
    base_path: /workspace/aiclipse/ComfyUI
    checkpoints: /workspace/aiclipse/models/checkpoints
    clip: /workspace/aiclipse/models/clip
    clip_vision: /workspace/aiclipse/models/clip_vision
    configs: /workspace/aiclipse/models/configs
    controlnet: /workspace/aiclipse/models/controlnet
    embeddings: /workspace/aiclipse/models/embeddings
    loras: /workspace/aiclipse/models/loras
    upscale_models: /workspace/aiclipse/models/upscale_models
    vae: /workspace/aiclipse/models/vae
    hypernetworks: /workspace/aiclipse/models/hypernetworks
    photomaker: /workspace/aiclipse/models/photomaker
    classifiers: /workspace/aiclipse/models/classifiers
    style_models: /workspace/aiclipse/models/style_models
    diffusers: /workspace/aiclipse/models/diffusers
    text_encoders: /workspace/aiclipse/models/text_encoders
    gligen: /workspace/aiclipse/models/gligen
    esrgan: /workspace/aiclipse/models/esrgan
YAML

    log_success "Enhanced model paths configured"
}

setup_manifest() {
    local manifest_file="/workspace/aiclipse/models_manifest.txt"

    # Initialize manifest if missing
    if [ ! -f "$manifest_file" ]; then
        # Try template-specific manifest first
        local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
        if [ -f "$template_manifest" ]; then
            cp "$template_manifest" "$manifest_file"
            log_info "Initialized with template manifest: ${TEMPLATE_TYPE}"
        # Fallback to environment variable
        elif [ -n "$MODELS_MANIFEST" ] && [ -f "$MODELS_MANIFEST" ]; then
            cp "$MODELS_MANIFEST" "$manifest_file"
            log_info "Initialized with environment manifest: $MODELS_MANIFEST"
        # Fallback to base manifest
        elif [ -f "/manifests/base_models.txt" ]; then
            cp "/manifests/base_models.txt" "$manifest_file"
            log_info "Initialized with base models manifest"
        else
            touch "$manifest_file"
            log_warn "No model manifest found - initialized empty manifest"
        fi
    fi

    # Always merge template manifest if available (to ensure required models are present)
    local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
    if [ -f "$template_manifest" ]; then
        log_info "Merging template manifest: ${TEMPLATE_TYPE}"
        # Append only unique lines
        while IFS= read -r line || [ -n "$line" ]; do
            [[ $line =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            if ! grep -Fxq "$line" "$manifest_file"; then
                echo "$line" >> "$manifest_file"
            fi
        done < "$template_manifest"
    fi
    
    return 0
}

generate_aria2_input() {
    local manifest_file="$1"
    local input_file="$2"
    
    rm -f "$input_file"
    
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ $line =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        
        # Parse line: source|identifier|filename|subdir[|checksum]
        IFS='|' read -r source identifier filename subdir checksum <<< "$line"
        
        source=$(echo "$source" | tr '[:upper:]' '[:lower:]' | xargs)
        identifier=$(echo "$identifier" | xargs)
        filename=$(echo "$filename" | xargs)
        subdir=$(echo "$subdir" | xargs)
        
        local url=""
        local header=""
        
        case "$source" in
            "huggingface"|"hf")
                url="https://huggingface.co/${identifier}/resolve/main/${filename}"
                if [ -n "$HF_TOKEN" ]; then
                    header="Authorization: Bearer $HF_TOKEN"
                fi
                ;;
            "civitai")
                url="https://civitai.com/api/download/models/${identifier}"
                if [ -n "$CIVITAI_TOKEN" ]; then
                    header="Authorization: Bearer $CIVITAI_TOKEN"
                fi
                ;;
            "url"|"direct")
                url="$identifier"
                ;;
            *)
                log_warn "Unknown source: $source for $filename"
                continue
                ;;
        esac
        
        if [ -n "$url" ]; then
            echo "$url" >> "$input_file"
            echo "  out=$filename" >> "$input_file"
            echo "  dir=/workspace/aiclipse/models/$subdir" >> "$input_file"
            if [ -n "$header" ]; then
                echo "  header=$header" >> "$input_file"
            fi
        fi
        
    done < "$manifest_file"
}

download_models_enhanced() {
    local manifest_file="/workspace/aiclipse/models_manifest.txt"
    local aria2_input="/workspace/aiclipse/aria2_input.txt"
    
    if [ "$DOWNLOAD_MODELS" != "true" ]; then
        log_info "Model downloads disabled (DOWNLOAD_MODELS=false)"
        return 0
    fi
    
    if ! setup_manifest; then
        return 0
    fi
    
    log_info "Generating download list..."
    generate_aria2_input "$manifest_file" "$aria2_input"
    
    if [ ! -s "$aria2_input" ]; then
        log_info "No valid downloads found in manifest."
        return 0
    fi
    
    log_info "🔥 Starting high-performance parallel downloads..."
    
    # Aria2c options:
    # -x 16: 16 connections per server
    # -s 16: 16 connections per file
    # -j 10: 10 parallel downloads
    # -c: Continue
    # --summary-interval=0: Reduce log noise
    
    if aria2c -i "$aria2_input" \
        -x 16 -s 16 -j 10 \
        -c --auto-file-renaming=false \
        --console-log-level=warn \
        --summary-interval=30; then
        log_success "All models downloaded successfully"
    else
        log_error "Some downloads failed"
    fi
    
    rm -f "$aria2_input"
}

download_models_async() {
    if [ "$DOWNLOAD_IN_FOREGROUND" = "true" ]; then
        download_models_enhanced
    else
        log_info "Starting model downloads in background..."
        mkdir -p /workspace/aiclipse/logs
        download_models_enhanced > /workspace/aiclipse/logs/models.log 2>&1 &
    fi
}
