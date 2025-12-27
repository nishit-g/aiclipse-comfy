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
    if ! is_true "${AUTO_UPDATE:-true}"; then
        log_info "Skipping auto-update (AUTO_UPDATE=false)"
        return 0
    fi

    log_step "Checking for updates from $CONFIG_REPO..."
    
    local temp_dir
    temp_dir=$(mktemp -d)
    local update_applied=false
    
    # Clone latest from GitHub
    if ! git clone --depth 1 -b "$CONFIG_BRANCH" "$CONFIG_REPO" "$temp_dir" >/dev/null 2>&1; then
        log_warn "Failed to fetch updates from $CONFIG_REPO"
        rm -rf "$temp_dir"
        return 0
    fi
    
    # =========================================================================
    # 1. UPDATE SCRIPTS
    # =========================================================================
    if [[ -d "$temp_dir/base/scripts" ]]; then
        if ! diff -rq "$temp_dir/base/scripts" "/scripts" >/dev/null 2>&1; then
            log_info "📦 Updating scripts..."
            rsync -a --delete "$temp_dir/base/scripts/" "/scripts/"
            chmod +x /scripts/*.sh /scripts/*.py 2>/dev/null || true
            chmod +x /scripts/lib/*.sh 2>/dev/null || true
            chmod +x /scripts/modules/*.sh 2>/dev/null || true
            update_applied=true
        fi
    fi
    
    # =========================================================================
    # 2. UPDATE TEMPLATE CONFIG
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
                update_applied=true
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
    # 3. UPDATE WORKFLOWS
    # =========================================================================
    if [[ -d "$template_dir/workflows" ]]; then
        local workflow_count
        workflow_count=$(find "$template_dir/workflows" -name "*.json" -type f 2>/dev/null | wc -l)
        
        if [[ "$workflow_count" -gt 0 ]]; then
            log_info "📦 Syncing $workflow_count workflow(s)..."
            ensure_dir "/opt/workflows"
            rsync -a "$template_dir/workflows/" "/opt/workflows/"
            update_applied=true
        fi
    fi
    
    # =========================================================================
    # 4. UPDATE BASE MANIFESTS
    # =========================================================================
    if [[ -d "$temp_dir/manifests" ]]; then
        ensure_dir "/manifests"
        rsync -a "$temp_dir/manifests/" "/manifests/"
    fi
    
    # =========================================================================
    # CLEANUP & RESTART IF NEEDED
    # =========================================================================
    rm -rf "$temp_dir"
    
    if [[ "$update_applied" == true ]]; then
        log_success "Updates applied!"
        
        # Save update timestamp
        ensure_dir "$WORKSPACE/state"
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$WORKSPACE/state/last_update"
        
        # Re-exec to use new scripts (only if scripts changed)
        if [[ -f "/scripts/start.sh" ]]; then
            log_warn "Restarting with updated scripts..."
            exec /scripts/start.sh "$@"
        fi
    else
        log_info "Already up to date"
    fi
}

# Run module
auto_update "$@"
