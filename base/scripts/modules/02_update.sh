#!/bin/bash
# =============================================================================
# Module 02: Auto-Update
# Checks for and applies updates from the config repository
# =============================================================================

check_and_update() {
    if ! is_true "${AUTO_UPDATE:-true}"; then
        log_info "Skipping auto-update (AUTO_UPDATE=false)"
        return 0
    fi

    log_step "Checking for updates from $CONFIG_REPO..."
    
    local temp_dir
    temp_dir=$(mktemp -d)
    
    if git clone --depth 1 -b "$CONFIG_BRANCH" "$CONFIG_REPO" "$temp_dir" >/dev/null 2>&1; then
        # Check if scripts have changed
        if ! diff -r "$temp_dir/base/scripts" "/scripts" >/dev/null 2>&1; then
            log_warn "Updates detected! Applying changes..."
            
            # Update scripts
            rsync -a "$temp_dir/base/scripts/" "/scripts/"
            chmod +x /scripts/*.sh /scripts/*.py 2>/dev/null || true
            chmod +x /scripts/lib/*.sh 2>/dev/null || true
            chmod +x /scripts/modules/*.sh 2>/dev/null || true
            
            # Update manifests
            if [[ -d "$temp_dir/manifests" ]]; then
                rsync -a "$temp_dir/manifests/" "/manifests/"
            fi
            
            log_success "Update complete. Reloading..."
            rm -rf "$temp_dir"
            
            # Re-exec self
            exec "$0" "$@"
        else
            log_info "Scripts are up to date"
        fi
    else
        log_warn "Failed to check for updates. Continuing with local scripts."
    fi
    
    rm -rf "$temp_dir"
}

# Run module
check_and_update "$@"
