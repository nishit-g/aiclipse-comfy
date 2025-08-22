#!/bin/bash

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
            log "✅ Template is up to date"
        fi
    else
        log "⚠️ Local version ($existing_version) is newer than template ($TEMPLATE_VERSION)"
    fi
}

perform_sync() {
    log "🔄 Syncing template files..."

    # Sync ComfyUI if needed
    if [ -d "/opt/ComfyUI" ] && [ ! -d "$COMFY_DIR" ]; then
        log "📦 Syncing ComfyUI installation..."
        rsync -av /opt/ComfyUI/ "$COMFY_DIR/"
    fi

    # Sync workflows if available
    if [ -d "/opt/workflows" ] && [ ! -d "/workspace/aiclipse/workflows" ]; then
        log "📋 Syncing workflows..."
        rsync -av /opt/workflows/ /workspace/aiclipse/workflows/
    fi
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
        "custom_args"
    ]
}
EOF
    log "💾 Saved template info: $TEMPLATE_VERSION_FILE"
}
