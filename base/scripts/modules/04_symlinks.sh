#!/bin/bash
# =============================================================================
# Module 04: Symlinks
# Creates convenient symlinks for user access
# =============================================================================

setup_symlinks() {
    log_step "Setting up symlinks for user convenience..."

    # Create user-friendly symlinks at /workspace root
    safe_link "/workspace/ComfyUI"     "$COMFY_DIR"
    safe_link "/workspace/workflows"   "$WORKFLOWS_DIR"
    safe_link "/workspace/models"      "$MODELS_DIR"
    safe_link "/workspace/logs"        "$LOGS_DIR"
    
    # Input/output links (after ComfyUI is installed)
    if dir_exists "$COMFY_DIR/input"; then
        safe_link "/workspace/input" "$COMFY_DIR/input"
    fi
    
    if dir_exists "$COMFY_DIR/output"; then
        safe_link "/workspace/output" "$COMFY_DIR/output"
    fi

    # Custom nodes link
    if dir_exists "$COMFY_DIR/custom_nodes"; then
        safe_link "/workspace/custom_nodes" "$COMFY_DIR/custom_nodes"
    fi
    
    log_success "Symlinks configured"
}

# Run module
setup_symlinks
