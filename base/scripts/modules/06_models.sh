#!/bin/bash
# =============================================================================
# Module 06: Model Setup
# Configures model paths and downloads models from various sources
# Supports: HuggingFace, R2, CivitAI via YAML config or legacy TXT manifest
# =============================================================================

setup_model_paths() {
    log_step "Configuring model paths..."
    
    ensure_dir "$MODELS_DIR"
    
    local comfy_models="$COMFY_DIR/models"
    
    # Already linked?
    if [[ -L "$comfy_models" && "$(readlink "$comfy_models")" == "$MODELS_DIR" ]]; then
        log_info "Models directory already linked"
        return 0
    fi
    
    # Migrate existing models and link
    if [[ -d "$comfy_models" && ! -L "$comfy_models" ]]; then
        log_info "Migrating existing models to persistent storage..."
        rsync -a --ignore-existing "$comfy_models/" "$MODELS_DIR/"
        rm -rf "$comfy_models"
    fi
    
    ln -sfn "$MODELS_DIR" "$comfy_models"
    log_success "Models linked: $comfy_models → $MODELS_DIR"
    
    # Remove obsolete extra_model_paths.yaml
    if file_exists "$COMFY_DIR/extra_model_paths.yaml"; then
        rm "$COMFY_DIR/extra_model_paths.yaml"
        log_info "Removed obsolete extra_model_paths.yaml"
    fi
}

download_models() {
    if ! is_true "${DOWNLOAD_MODELS:-true}"; then
        log_info "Model downloads disabled (DOWNLOAD_MODELS=false)"
        return 0
    fi
    
    log_step "Starting model downloads..."
    
    # Config lookup order:
    # 1. /config/config.yaml (synced from GitHub at runtime)
    # 2. /templates/{type}/config.yaml (baked in image)
    # 3. Legacy TXT manifests
    local config=""
    
    if file_exists "/config/config.yaml"; then
        config="/config/config.yaml"
        log_info "Using synced config: $config"
    elif file_exists "/templates/${TEMPLATE_TYPE}/config.yaml"; then
        config="/templates/${TEMPLATE_TYPE}/config.yaml"
        log_info "Using image config: $config"
    fi
    
    if [[ -n "$config" ]]; then
        download_from_yaml "$config"
    else
        # Fallback to legacy manifest
        local manifest="/workspace/aiclipse/models_manifest.txt"
        local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
        
        if file_exists "$manifest"; then
            log_info "Using legacy manifest: $manifest"
            download_from_manifest "$manifest"
        elif file_exists "$template_manifest"; then
            log_info "Using template manifest: $template_manifest"
            cp "$template_manifest" "$manifest"
            download_from_manifest "$manifest"
        else
            log_warn "No model config or manifest found"
        fi
    fi
}

download_from_yaml() {
    local config="$1"
    local aria2_input
    aria2_input=$(mktemp)
    local python_manifest
    python_manifest=$(mktemp)
    
    # Parse YAML and generate download lists
    yaml_list "$config" "models" | while read -r item; do
        local source repo file path key
        source=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('source',''))")
        
        case "$source" in
            huggingface|hf)
                repo=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('repo',''))")
                file=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('file',''))")
                path=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('path',''))")
                
                local url="https://huggingface.co/${repo}/resolve/main/${file}"
                
                echo "$url" >> "$aria2_input"
                echo "  out=$file" >> "$aria2_input"
                echo "  dir=$MODELS_DIR/$path" >> "$aria2_input"
                
                if [[ -n "${HF_TOKEN:-}" ]]; then
                    echo "  header=Authorization: Bearer $HF_TOKEN" >> "$aria2_input"
                fi
                ;;
            r2|cloudflare)
                key=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('key',''))")
                file=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('file',''))")
                path=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('path',''))")
                
                echo "r2|$key|$file|$path" >> "$python_manifest"
                ;;
            *)
                log_warn "Unknown source: $source"
                ;;
        esac
    done
    
    # Run aria2c for HTTP downloads
    if [[ -s "$aria2_input" ]]; then
        log_info "Starting parallel downloads (aria2c)..."
        aria2c -i "$aria2_input" \
            -x 16 -s 16 -j 10 \
            -c --auto-file-renaming=false \
            --console-log-level=warn \
            --summary-interval=30 || log_warn "Some aria2c downloads failed"
    fi
    
    # Run Python for R2 downloads
    if [[ -s "$python_manifest" ]]; then
        log_info "Starting R2 downloads (Python)..."
        "$VENV_PATH/bin/python" /scripts/download_models.py \
            --manifest "$python_manifest" \
            --models-dir "$MODELS_DIR" || log_warn "Some R2 downloads failed"
    fi
    
    rm -f "$aria2_input" "$python_manifest"
    log_success "Model downloads complete"
}

download_from_manifest() {
    local manifest="$1"
    
    # Use the existing setup_models.sh functions
    source /scripts/setup_models.sh
    download_models_enhanced
}

# Run module
setup_model_paths
if is_true "${DOWNLOAD_IN_FOREGROUND:-false}"; then
    download_models
else
    log_info "Starting model downloads in background..."
    ensure_dir "$LOGS_DIR"
    download_models > "$LOGS_DIR/models.log" 2>&1 &
fi
