#!/bin/bash
# Fixed setup_sync.sh - Proper ComfyUI Workflow Integration

sync_template_if_needed() {
    log "🔄 Checking template version sync..."

    local existing_version="0.0.0"
    if [ -f "$TEMPLATE_VERSION_FILE" ]; then
        existing_version=$(jq -r '.template_version // "0.0.0"' "$TEMPLATE_VERSION_FILE" 2>/dev/null || echo "0.0.0")
    fi

    log "📋 Current: $existing_version, Template: $TEMPLATE_VERSION"

    # Version comparison
    if [ "$(printf '%s\n' "$existing_version" "$TEMPLATE_VERSION" | sort -V | head -n 1)" = "$existing_version" ]; then
        if [ "$existing_version" != "$TEMPLATE_VERSION" ]; then
            log "⬆️ Upgrading template from $existing_version to $TEMPLATE_VERSION"
            perform_sync
            save_template_json
        else
            log "✅ Template is up to date, ensuring workflows are synced"
            sync_workflows_to_comfyui
        fi
    else
        log "⚠️ Local version ($existing_version) is newer than template ($TEMPLATE_VERSION)"
        sync_workflows_to_comfyui
    fi
}

perform_sync() {
    log "🔄 Syncing template files..."

    # Sync ComfyUI if needed
    if [ -d "/opt/ComfyUI" ] && [ ! -d "$COMFY_DIR" ]; then
        log "📦 Syncing ComfyUI installation..."
        rsync -av /opt/ComfyUI/ "$COMFY_DIR/"
    fi

    # Sync workflows to proper ComfyUI locations
    sync_workflows_to_comfyui
}

# NEW: Proper ComfyUI workflow sync based on research findings
sync_workflows_to_comfyui() {
    log "🎨 Syncing workflows to ComfyUI directories..."

    # Ensure ComfyUI directory exists
    if [ ! -d "$COMFY_DIR" ]; then
        log "⚠️ ComfyUI directory not found, workflows will sync later"
        return 0
    fi

    # Create workspace workflows directory
    mkdir -p /workspace/aiclipse/workflows

    # Step 1: Sync template workflows to workspace
    if [ -d "/opt/workflows" ]; then
        log "📋 Syncing template workflows to workspace..."
        rsync -av /opt/workflows/ /workspace/aiclipse/workflows/

        local workflow_count=$(find /workspace/aiclipse/workflows -name "*.json" -type f | wc -l)
        log "✅ Synced $workflow_count workflow(s) from template"
    else
        log "ℹ️ No template workflows found in /opt/workflows"
    fi

    # Step 2: Create ComfyUI user/default/workflows directory (modern ComfyUI)
    local comfy_user_workflows="$COMFY_DIR/user/default/workflows"
    mkdir -p "$comfy_user_workflows"

    # Step 3: Copy workflows to ComfyUI's expected location
    if [ -d "/workspace/aiclipse/workflows" ]; then
        log "🎯 Copying workflows to ComfyUI user directory..."
        find /workspace/aiclipse/workflows -name "*.json" -type f -exec cp {} "$comfy_user_workflows/" \;

        local copied_count=$(find "$comfy_user_workflows" -name "*.json" -type f | wc -l)
        log "✅ Copied $copied_count workflow(s) to ComfyUI user directory"
    fi

    # Step 4: Configure Custom Scripts extension if available
    setup_custom_scripts_workflows

    # Step 5: Create symlinks for easy access
    setup_workflow_symlinks

    # Step 6: List available workflows for debugging
    list_workflows_debug
}

# Configure ComfyUI-Custom-Scripts for workflow management
setup_custom_scripts_workflows() {
    local custom_scripts_dir="$COMFY_DIR/custom_nodes/ComfyUI-Custom-Scripts"
    local pysssss_config="$custom_scripts_dir/pysssss.json"

    if [ -d "$custom_scripts_dir" ]; then
        log "🔧 Configuring Custom Scripts workflow directory..."

        # Create or update pysssss.json
        if [ -f "$pysssss_config" ]; then
            # Backup existing config
            cp "$pysssss_config" "${pysssss_config}.bak"
        fi

        # Create updated config with workflows directory
        cat > "$pysssss_config" << 'EOF'
{
    "name": "CustomScripts",
    "logging": false,
    "workflows": {
        "directory": "/workspace/aiclipse/workflows"
    }
}
EOF
        log "✅ Custom Scripts configured to use /workspace/aiclipse/workflows"
    else
        log "ℹ️ Custom Scripts extension not found, skipping configuration"
    fi
}

# Create symlinks for workflow access
setup_workflow_symlinks() {
    log "🔗 Creating workflow access symlinks..."

    # Main workspace symlink
    if [ ! -L "/workspace/workflows" ]; then
        ln -sf /workspace/aiclipse/workflows /workspace/workflows
        log "🔗 Created: /workspace/workflows -> /workspace/aiclipse/workflows"
    fi

    # ComfyUI direct access symlink
    if [ -d "$COMFY_DIR" ] && [ ! -L "$COMFY_DIR/workflows" ]; then
        ln -sf /workspace/aiclipse/workflows "$COMFY_DIR/workflows"
        log "🔗 Created: $COMFY_DIR/workflows -> /workspace/aiclipse/workflows"
    fi

    # Alternative access in ComfyUI input directory
    if [ -d "$COMFY_DIR/input" ]; then
        mkdir -p "$COMFY_DIR/input"
        if [ ! -L "$COMFY_DIR/input/workflows" ]; then
            ln -sf /workspace/aiclipse/workflows "$COMFY_DIR/input/workflows"
            log "🔗 Created: $COMFY_DIR/input/workflows -> /workspace/aiclipse/workflows"
        fi
    fi
}

# Debug function to list available workflows
list_workflows_debug() {
    log "📁 Workflow locations summary:"

    # Template workflows
    if [ -d "/opt/workflows" ]; then
        local template_count=$(find /opt/workflows -name "*.json" -type f 2>/dev/null | wc -l)
        log "  📦 Template workflows: $template_count"
    fi

    # Workspace workflows
    if [ -d "/workspace/aiclipse/workflows" ]; then
        local workspace_count=$(find /workspace/aiclipse/workflows -name "*.json" -type f 2>/dev/null | wc -l)
        log "  🎯 Workspace workflows: $workspace_count"
    fi

    # ComfyUI user workflows
    local comfy_user_workflows="$COMFY_DIR/user/default/workflows"
    if [ -d "$comfy_user_workflows" ]; then
        local comfy_count=$(find "$comfy_user_workflows" -name "*.json" -type f 2>/dev/null | wc -l)
        log "  👤 ComfyUI user workflows: $comfy_count"
    fi

    # List actual workflow files
    if [ -d "/workspace/aiclipse/workflows" ]; then
        local workflow_files=$(find /workspace/aiclipse/workflows -name "*.json" -type f 2>/dev/null)
        if [ -n "$workflow_files" ]; then
            log "📋 Available workflows:"
            echo "$workflow_files" | sed 's/.*\//  - /'
        fi
    fi

    log "🎨 How to access workflows in ComfyUI:"
    log "  1. Drag & Drop: Drag JSON files from file browser onto ComfyUI"
    log "  2. Menu: Workflow → Browse Workflow Templates"
    log "  3. File Browser: http://your-ip:8080 → workflows/"
    log "  4. Direct path: /workspace/workflows/"
}

save_template_json() {
    cat > "$TEMPLATE_VERSION_FILE" << EOF
{
    "template_name": "aiclipse-${TEMPLATE_TYPE}",
    "template_version": "${TEMPLATE_VERSION}",
    "gpu_type": "${GPU_TYPE:-unknown}",
    "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "features": [
        "filebrowser",
        "zasper",
        "ssh",
        "symlinks",
        "model_manifest",
        "custom_args",
        "comfyui_workflows"
    ],
    "workflows_synced": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    log "💾 Saved template info: $TEMPLATE_VERSION_FILE"
}
