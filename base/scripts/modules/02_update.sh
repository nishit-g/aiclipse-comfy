#!/bin/bash
# =============================================================================
# Module 02: Auto-Update
# Enterprise-grade auto-update from GitHub repository
# 
# Syncs at runtime (no rebuild needed):
#   - Scripts (/scripts/)
#   - Config (config.yaml)
#   - Manifests (models, nodes)
#   - Workflows
# =============================================================================

auto_update() {
    # Guard against infinite restart loops
    local guard_file="$WORKSPACE/state/.update_in_progress"
    if [[ -f "$guard_file" ]]; then
        local guard_age=$(($(date +%s) - $(stat -c %Y "$guard_file" 2>/dev/null || echo 0)))
        if [[ "$guard_age" -lt 30 ]]; then
            log_info "Update already in progress, skipping"
            rm -f "$guard_file"
            return 0
        fi
    fi
    
    if ! is_true "${AUTO_UPDATE:-true}"; then
        log_info "Skipping auto-update (AUTO_UPDATE=false)"
        return 0
    fi
    
    # Skip if recently updated (within 5 minutes) - saves ~3s
    local last_update="$WORKSPACE/state/last_update"
    if [[ -f "$last_update" ]]; then
        local age=$(($(date +%s) - $(stat -c %Y "$last_update" 2>/dev/null || echo 0)))
        if [[ "$age" -lt 300 ]]; then
            log_info "Skipping update (checked ${age}s ago)"
            return 0
        fi
    fi

    log_step "Checking for updates from $CONFIG_REPO..."
    
    local temp_dir
    temp_dir=$(mktemp -d)
    local scripts_changed=false
    local config_changed=false
    
    # Clone latest from GitHub
    if ! git clone --depth 1 -b "$CONFIG_BRANCH" "$CONFIG_REPO" "$temp_dir" >/dev/null 2>&1; then
        log_warn "Failed to fetch updates from $CONFIG_REPO"
        rm -rf "$temp_dir"
        return 0
    fi
    
    # =========================================================================
    # 1. UPDATE SCRIPTS (only this triggers restart)
    # =========================================================================
    if [[ -d "$temp_dir/base/scripts" ]]; then
        if ! diff -rq "$temp_dir/base/scripts" "/scripts" >/dev/null 2>&1; then
            log_info "📦 Updating scripts..."
            rsync -a --delete "$temp_dir/base/scripts/" "/scripts/"
            chmod +x /scripts/*.sh /scripts/*.py 2>/dev/null || true
            chmod +x /scripts/lib/*.sh 2>/dev/null || true
            chmod +x /scripts/modules/*.sh 2>/dev/null || true
            scripts_changed=true
        fi
    fi
    
    # =========================================================================
    # 2. UPDATE TEMPLATE CONFIG (no restart needed)
    # =========================================================================
    local template_dir="$temp_dir/templates/${TEMPLATE_TYPE}"
    local config_dir="/config"
    ensure_dir "$config_dir"
    
    if [[ -d "$template_dir" ]]; then
        # Sync config.yaml
        if [[ -f "$template_dir/config.yaml" ]]; then
            if ! diff -q "$template_dir/config.yaml" "$config_dir/config.yaml" >/dev/null 2>&1; then
                log_info "📦 Updating config.yaml..."
                cp "$template_dir/config.yaml" "$config_dir/config.yaml"
                config_changed=true
            fi
        fi
        
        # Sync models manifest (legacy support)
        if [[ -f "$template_dir/models_manifest.txt" ]]; then
            cp "$template_dir/models_manifest.txt" "/manifests/${TEMPLATE_TYPE}_models.txt"
        fi
        
        # Sync nodes manifest (legacy support)
        if [[ -f "$template_dir/nodes_manifest.txt" ]]; then
            cp "$template_dir/nodes_manifest.txt" "/manifests/${TEMPLATE_TYPE}_nodes.txt"
        fi
    fi
    
    # =========================================================================
    # 3. UPDATE WORKFLOWS (no restart needed)
    # =========================================================================
    if [[ -d "$template_dir/workflows" ]]; then
        ensure_dir "/opt/workflows"
        # Use rsync with --checksum to only copy if content differs
        if rsync -a --checksum --itemize-changes "$template_dir/workflows/" "/opt/workflows/" 2>/dev/null | grep -q '^>'; then
            local workflow_count
            workflow_count=$(find "$template_dir/workflows" -name "*.json" -type f 2>/dev/null | wc -l)
            log_info "📦 Syncing $workflow_count workflow(s)..."
        fi
    fi
    
    # =========================================================================
    # 4. UPDATE BASE MANIFESTS (no restart needed)
    # =========================================================================
    if [[ -d "$temp_dir/manifests" ]]; then
        ensure_dir "/manifests"
        rsync -a "$temp_dir/manifests/" "/manifests/"
    fi
    
    # =========================================================================
    # CLEANUP & RESTART ONLY IF SCRIPTS CHANGED
    # =========================================================================
    rm -rf "$temp_dir"
    
    # Save update timestamp
    ensure_dir "$WORKSPACE/state"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$WORKSPACE/state/last_update"
    
    if [[ "$scripts_changed" == true ]]; then
        log_success "Scripts updated!"
        
        # Set guard before restart
        touch "$guard_file"
        
        # Re-exec to use new scripts
        if [[ -f "/scripts/start.sh" ]]; then
            log_warn "Restarting with updated scripts..."
            exec /scripts/start.sh "$@"
        fi
    elif [[ "$config_changed" == true ]]; then
        log_success "Config updated (no restart needed)"
    else
        log_info "Already up to date"
    fi
}

# Run module
auto_update "$@"
