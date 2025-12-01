#!/bin/bash
# Enhanced Model Setup Script with Aria2c Parallel Downloads

setup_model_paths() {
    log_info "Configuring ComfyUI model paths..."

    # Strategy: Symlink the entire models directory
    # This is more robust than extra_model_paths.yaml because it automatically
    # handles ANY new model folder types added by custom nodes.

    local comfy_models_dir="$COMFY_DIR/models"
    local persistent_models_dir="/workspace/aiclipse/models"

    # Ensure persistent directory exists
    mkdir -p "$persistent_models_dir"

    # If ComfyUI/models is already a symlink to our target, we are good
    if [ -L "$comfy_models_dir" ] && [ "$(readlink "$comfy_models_dir")" = "$persistent_models_dir" ]; then
        log_success "Models directory already linked"
        return 0
    fi

    # If it's a real directory (fresh install), we need to migrate and link
    if [ -d "$comfy_models_dir" ] && [ ! -L "$comfy_models_dir" ]; then
        log_info "🔄 Migrating default model folders to persistent storage..."
        
        # Move any existing files/folders from ComfyUI/models to persistent storage
        # use rsync to merge (flags: archive, no-overwrite-newer, verbose)
        rsync -a --ignore-existing "$comfy_models_dir/" "$persistent_models_dir/"
        
        # Remove the original directory
        rm -rf "$comfy_models_dir"
    fi

    # Create the symlink
    ln -sfn "$persistent_models_dir" "$comfy_models_dir"
    log_success "🔗 Linked: $comfy_models_dir -> $persistent_models_dir"
    
    # We no longer need extra_model_paths.yaml for the main models
    # But we remove it if it exists to avoid confusion/conflicts
    if [ -f "$COMFY_DIR/extra_model_paths.yaml" ]; then
        rm "$COMFY_DIR/extra_model_paths.yaml"
        log_info "🗑️ Removed obsolete extra_model_paths.yaml"
    fi
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

    # Smart Merge: Update existing entries based on FILENAME
    local template_manifest="/manifests/${TEMPLATE_TYPE}_models.txt"
    if [ -f "$template_manifest" ]; then
        log_info "Merging template manifest: ${TEMPLATE_TYPE}"
        while IFS= read -r line || [ -n "$line" ]; do
            [[ $line =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            
            # Extract filename (3rd field)
            local filename=$(echo "$line" | cut -d'|' -f3 | xargs)
            
            # Get existing entries for this filename
            local existing_entries=$(grep "|${filename}|" "$manifest_file" || true)
            
            if [ -n "$existing_entries" ]; then
                # If existing entries do not exactly match the single new line
                # This handles duplicates or incorrect URLs
                if [ "$existing_entries" != "$line" ]; then
                    log_info "🔄 Updating manifest entry for $filename"
                    
                    # Escape special chars for sed
                    local escaped_filename=$(echo "$filename" | sed 's/[#]/\\#/g')
                    
                    # Delete ALL lines matching this filename
                    sed -i "/|${escaped_filename}|/d" "$manifest_file"
                    
                    # Append the correct line
                    echo "$line" >> "$manifest_file"
                fi
            else
                # New entry, append
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
    local python_manifest="/workspace/aiclipse/python_manifest.txt"
    
    if [ "$DOWNLOAD_MODELS" != "true" ]; then
        log_info "Model downloads disabled (DOWNLOAD_MODELS=false)"
        return 0
    fi
    
    if ! setup_manifest; then
        return 0
    fi
    
    log_info "Generating download lists..."
    
    # Clear previous lists
    rm -f "$aria2_input" "$python_manifest"
    touch "$aria2_input" "$python_manifest"
    
    # Split downloads between Aria2 and Python script
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
        local use_aria2=false
        
        case "$source" in
            "huggingface"|"hf")
                url="https://huggingface.co/${identifier}/resolve/main/${filename}"
                if [ -n "$HF_TOKEN" ]; then
                    header="Authorization: Bearer $HF_TOKEN"
                fi
                use_aria2=true
                ;;
            "civitai")
                url="https://civitai.com/api/download/models/${identifier}"
                if [ -n "$CIVITAI_TOKEN" ]; then
                    header="Authorization: Bearer $CIVITAI_TOKEN"
                fi
                use_aria2=true
                ;;
            "url"|"direct")
                url="$identifier"
                use_aria2=true
                ;;
            "r2"|"cloudflare")
                # R2 goes to python script
                echo "$line" >> "$python_manifest"
                continue
                ;;
            *)
                # Unknown sources go to python script as fallback
                echo "$line" >> "$python_manifest"
                continue
                ;;
        esac
        
        if [ "$use_aria2" = "true" ] && [ -n "$url" ]; then
            echo "$url" >> "$aria2_input"
            echo "  out=$filename" >> "$aria2_input"
            echo "  dir=/workspace/aiclipse/models/$subdir" >> "$aria2_input"
            if [ -n "$header" ]; then
                echo "  header=$header" >> "$aria2_input"
            fi
        fi
        
    done < "$manifest_file"
    
    # 1. Run Aria2 downloads
    if [ -s "$aria2_input" ]; then
        log_info "🔥 Starting high-performance parallel downloads (Aria2)..."
        if aria2c -i "$aria2_input" \
            -x 16 -s 16 -j 10 \
            -c --auto-file-renaming=false \
            --console-log-level=warn \
            --summary-interval=30; then
            log_success "Aria2 downloads completed"
        else
            log_error "Some Aria2 downloads failed"
        fi
    else
        log_info "No standard downloads found for Aria2."
    fi
    
    # 2. Run Python downloads (R2, etc)
    if [ -s "$python_manifest" ]; then
        log_info "🐍 Starting specialized downloads (R2/Python)..."
        if /venv/bin/python /scripts/download_models.py --manifest "$python_manifest" --models-dir "/workspace/aiclipse/models"; then
            log_success "Python downloads completed"
        else
            log_error "Some Python downloads failed"
        fi
    fi
    
    # Cleanup
    rm -f "$aria2_input" "$python_manifest"
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
