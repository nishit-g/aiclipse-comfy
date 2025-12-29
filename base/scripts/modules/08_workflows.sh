#!/bin/bash
# =============================================================================
# Module 08: Workflow Sync
# Syncs workflows from template to ComfyUI directories
# =============================================================================

sync_workflows() {
    log_step "Syncing workflows..."
    
    ensure_dir "$WORKFLOWS_DIR"
    
    # Sync from template
    if dir_exists "/opt/workflows"; then
        log_info "Copying template workflows..."
        rsync -av /opt/workflows/ "$WORKFLOWS_DIR/"
        
        local count
        count=$(find "$WORKFLOWS_DIR" -name "*.json" -type f | wc -l)
        log_info "Synced $count workflow(s) from template"
    fi
    
    # Create ComfyUI user workflow directory
    local comfy_user_workflows="$COMFY_DIR/user/default/workflows"
    ensure_dir "$comfy_user_workflows"
    
    # Copy workflows to ComfyUI
    # On Modal, always force-copy since there's no persistent user data
    if dir_exists "$WORKFLOWS_DIR"; then
        local should_force=false
        
        if is_true "${FORCE_WORKFLOW_RESET:-false}"; then
            should_force=true
            log_warn "FORCE_WORKFLOW_RESET: Overwriting existing workflows"
        elif [[ -n "${MODAL_MODELS_PATH:-}" ]]; then
            # On Modal, always force since we don't persist user directory
            should_force=true
        fi
        
        if [[ "$should_force" == true ]]; then
            find "$WORKFLOWS_DIR" -name "*.json" -type f -exec cp -f {} "$comfy_user_workflows/" \;
        else
            find "$WORKFLOWS_DIR" -name "*.json" -type f -exec cp -n {} "$comfy_user_workflows/" \;
        fi
        
        # Create .index.json for ComfyUI workflow discovery
        # This file lists all workflows available in the directory
        local index_file="$comfy_user_workflows/.index.json"
        echo "[" > "$index_file"
        local first=true
        for wf in "$comfy_user_workflows"/*.json; do
            if [[ -f "$wf" && "$(basename "$wf")" != ".index.json" ]]; then
                local name=$(basename "$wf")
                if [[ "$first" == true ]]; then
                    first=false
                else
                    echo "," >> "$index_file"
                fi
                echo "  \"$name\"" >> "$index_file"
            fi
        done
        echo "]" >> "$index_file"
        log_info "Created workflow index: $index_file"
    fi
    
    # Create symlinks for easy access
    safe_link "$COMFY_DIR/workflows" "$WORKFLOWS_DIR"
    
    if dir_exists "$COMFY_DIR/input"; then
        ensure_dir "$COMFY_DIR/input"
        safe_link "$COMFY_DIR/input/workflows" "$WORKFLOWS_DIR"
    fi
    
    log_success "Workflows synced"
}

save_template_info() {
    local info_file="$WORKSPACE/template.json"
    
    cat > "$info_file" << EOF
{
    "template_name": "aiclipse-${TEMPLATE_TYPE}",
    "template_version": "${TEMPLATE_VERSION}",
    "aiclipse_version": "${AICLIPSE_VERSION}",
    "gpu_type": "${GPU_TYPE}",
    "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "workflows_synced": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    log_debug "Template info saved to $info_file"
}

# Run module
sync_workflows
save_template_info
