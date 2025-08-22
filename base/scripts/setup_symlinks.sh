#!/bin/bash

setup_symlinks() {
    log "🔗 Setting up symlinks for user convenience..."

    # Robust symlink creator (backs up existing)
    safe_link() {
        local link="$1" target="$2"
        if [ -e "$link" ] && [ ! -L "$link" ]; then
            mv "$link" "${link}.bak.$(date +%s)"
            log "📦 Backed up existing: $link"
        fi
        ln -sfnT "$target" "$link"
        log "🔗 Linked: $link -> $target"
    }

    # Create user-friendly symlinks at /workspace root
    safe_link "/workspace/ComfyUI"   "/workspace/aiclipse/ComfyUI"
    safe_link "/workspace/workflows" "/workspace/aiclipse/workflows"
    safe_link "/workspace/input"     "/workspace/aiclipse/ComfyUI/input"
    safe_link "/workspace/output"    "/workspace/aiclipse/ComfyUI/output"
    safe_link "/workspace/models"    "/workspace/aiclipse/models"
    safe_link "/workspace/logs"      "/workspace/aiclipse/logs"

    # Additional convenience links
    if [ -d "/workspace/aiclipse/ComfyUI/custom_nodes" ]; then
        safe_link "/workspace/custom_nodes" "/workspace/aiclipse/ComfyUI/custom_nodes"
    fi
}
