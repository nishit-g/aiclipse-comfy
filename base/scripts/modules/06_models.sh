#!/bin/bash
# =============================================================================
# Module 06: Model Setup
# Configures model paths and downloads models from various sources
# Supports: HuggingFace, R2, CivitAI via YAML config or legacy TXT manifest
# =============================================================================

setup_model_paths() {
    log_step "Configuring model paths..."
    
    ensure_dir "$MODELS_DIR"
    
    # Create ALL expected model subdirectories so ComfyUI UI shows them
    # Even empty folders need to exist for the model picker to work
    local expected_subdirs="checkpoints unet vae loras text_encoders embeddings controlnet diffusion_models clip upscale_models ipadapter hypernetworks custom_nodes"
    for subdir in $expected_subdirs; do
        ensure_dir "$MODELS_DIR/$subdir"
    done
    
    # =========================================================================
    # MODAL VOLUME INTEGRATION
    # If MODAL_MODELS_PATH is set (by Modal serve.py), check for pre-downloaded models
    # NOTE: We use extra_model_paths.yaml (created by serve.py) instead of symlinks
    # =========================================================================
    if [[ -n "${MODAL_MODELS_PATH:-}" && -d "$MODAL_MODELS_PATH" ]]; then
        log_info "Modal Volume detected at $MODAL_MODELS_PATH"
        
        # Check if Volume has models
        local volume_model_count=$(find "$MODAL_MODELS_PATH" -name "*.safetensors" 2>/dev/null | wc -l)
        
        if [[ "$volume_model_count" -gt 0 ]]; then
            log_success "Found $volume_model_count pre-downloaded models in Modal Volume"
            
            # COMMENTED OUT: Symlink creation
            # We now use extra_model_paths.yaml instead of symlinks for Modal
            # The yaml points ComfyUI directly to /modal-volumes/models
            # This avoids conflicts between symlinks and ComfyUI's own models/ dir
            #
            # for subdir in checkpoints unet vae loras text_encoders embeddings controlnet diffusion_models clip upscale_models; do
            #     local vol_subdir="$MODAL_MODELS_PATH/$subdir"
            #     local models_subdir="$MODELS_DIR/$subdir"
            #     
            #     if [[ -d "$vol_subdir" ]] && [[ -n "$(ls -A "$vol_subdir" 2>/dev/null)" ]]; then
            #         ensure_dir "$(dirname "$models_subdir")"
            #         
            #         if [[ -L "$models_subdir" ]]; then
            #             rm "$models_subdir"
            #         elif [[ -d "$models_subdir" ]]; then
            #             rm -rf "$models_subdir"
            #         fi
            #         
            #         ln -sfn "$vol_subdir" "$models_subdir"
            #         local file_count=$(ls -1 "$vol_subdir" 2>/dev/null | wc -l)
            #         log_info "🔗 Linked: $subdir ($file_count files from Modal Volume)"
            #     fi
            # done
            
            # Skip downloads since we have pre-cached models
            export SKIP_MODEL_DOWNLOAD=true
            log_success "Using pre-downloaded models from Modal Volume (via extra_model_paths.yaml)"
        fi
    fi
    # =========================================================================
    
    # =========================================================================
    # ON MODAL: Skip symlink setup below - we use extra_model_paths.yaml instead
    # The symlink approach (ComfyUI/models → $MODELS_DIR) conflicts with YAML approach
    # =========================================================================
    if [[ -n "${MODAL_MODELS_PATH:-}" ]]; then
        log_info "Modal detected - using extra_model_paths.yaml (no symlinks)"
        return 0
    fi
    
    # =========================================================================
    # NON-MODAL (RunPod, local): Use symlink approach
    # =========================================================================
    
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
    
    # Remove extra_model_paths.yaml on non-Modal environments (we use symlinks instead)
    if file_exists "$COMFY_DIR/extra_model_paths.yaml"; then
        rm "$COMFY_DIR/extra_model_paths.yaml"
        log_info "Removed extra_model_paths.yaml (using symlinks instead)"
    fi
}

download_models() {
    # Check if we should skip downloads (set by Modal Volume integration)
    if is_true "${SKIP_MODEL_DOWNLOAD:-false}"; then
        log_success "Skipping model downloads - using pre-downloaded models from Modal Volume"
        return 0
    fi
    
    if ! is_true "${DOWNLOAD_MODELS:-true}"; then
        log_info "Model downloads disabled (DOWNLOAD_MODELS=false)"
        return 0
    fi
    
    log_step "Starting model downloads..."
    
    # Enable HuggingFace XET protocol for 10x faster downloads
    export HF_XET_HIGH_PERFORMANCE=1
    export HF_HUB_ENABLE_HF_TRANSFER=1
    
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
        log_warn "No model config found - create config.yaml in /config/ or /templates/${TEMPLATE_TYPE}/"
    fi
}

download_from_yaml() {
    local config="$1"
    local aria2_input
    aria2_input=$(mktemp)
    local python_manifest
    python_manifest=$(mktemp)
    local model_count=0
    
    # Parse YAML and generate download lists (use jq for fast JSON parsing)
    yaml_list "$config" "models" | while read -r item; do
        # Single jq call per model (faster than 4 separate calls)
        read -r source repo file path key <<< $(echo "$item" | jq -r '[.source//"hf",.repo//"",.file//"",.path//"",.key//""] | @tsv')
        
        case "$source" in
            huggingface|hf)
                [[ -z "$repo" || -z "$file" ]] && continue
                
                local target_file="$MODELS_DIR/$path/$file"
                if [[ -f "$target_file" ]]; then
                    local size_mb=$(du -m "$target_file" 2>/dev/null | cut -f1)
                    log_info "⏭️ Exists: $file (${size_mb}MB)"
                    continue
                fi
                
                log_info "📥 Queued: $file"
                
                local url="https://huggingface.co/${repo}/resolve/main/${file}"
                
                echo "$url" >> "$aria2_input"
                echo "  out=$file" >> "$aria2_input"
                echo "  dir=$MODELS_DIR/$path" >> "$aria2_input"
                
                if [[ -n "${HF_TOKEN:-}" ]]; then
                    echo "  header=Authorization: Bearer $HF_TOKEN" >> "$aria2_input"
                fi
                model_count=$((model_count + 1))
                ;;
            r2|cloudflare)
                # key, file, path already parsed from single jq call above
                [[ -z "$key" || -z "$file" ]] && continue
                
                log_info "📥 Queued: $file (R2)"
                echo "r2|$key|$file|$path" >> "$python_manifest"
                model_count=$((model_count + 1))
                ;;
            *)
                log_warn "Unknown source: $source"
                ;;
        esac
    done
    
    # Run aria2c for HTTP downloads (optimized for speed)
    if [[ -s "$aria2_input" ]]; then
        local hf_count=$(grep -c "^https://" "$aria2_input" 2>/dev/null || echo 0)
        log_info "🚀 Downloading $hf_count models from HuggingFace (parallel)..."
        aria2c -i "$aria2_input" \
            -x 16 -s 16 -j 8 \
            -c --auto-file-renaming=false \
            --file-allocation=none \
            --disk-cache=64M \
            --console-log-level=notice \
            --summary-interval=15 2>&1 | grep -E "Download|OK|ERR|\[#" || log_warn "Some aria2c downloads failed"
    fi
    
    # Run Python for R2 downloads
    if [[ -s "$python_manifest" ]]; then
        log_info "☁️ Starting R2 downloads..."
        "$VENV_PATH/bin/python" /scripts/download_models.py \
            --manifest "$python_manifest" \
            --models-dir "$MODELS_DIR" || log_warn "Some R2 downloads failed"
    fi
    
    rm -f "$aria2_input" "$python_manifest"
    
    # Show summary with disk usage
    local total_size=$(du -sh "$MODELS_DIR" 2>/dev/null | cut -f1)
    log_success "Model downloads complete - Total: ${total_size:-unknown}"
}

# Run module
setup_model_paths

# Run downloads (foreground by default for visibility)
if is_true "${DOWNLOAD_IN_BACKGROUND:-false}"; then
    log_info "Starting model downloads in background..."
    ensure_dir "$LOGS_DIR"
    download_models > "$LOGS_DIR/models.log" 2>&1 &
    log_info "Model logs: $LOGS_DIR/models.log"
else
    download_models
fi
