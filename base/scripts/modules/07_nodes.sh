#!/bin/bash
# =============================================================================
# Module 07: Custom Nodes Installation
# Installs custom nodes from YAML config or legacy TXT manifest
# Uses parallel installation for speed
# =============================================================================

install_single_node() {
    local repo_url="$1"
    local branch="${2:-main}"
    local nodes_dir="$3"
    
    local node_name
    node_name=$(basename "$repo_url" .git)
    local node_path="$nodes_dir/$node_name"
    
    if [[ ! -d "$node_path" ]]; then
        echo "⬇️ Cloning $node_name..."
        if ! git clone --depth 1 -b "$branch" "$repo_url" "$node_path" 2>/dev/null; then
            echo "❌ Failed to clone $node_name"
            return 1
        fi
        echo "✨ Cloned $node_name"
    else
        echo "✅ $node_name already exists"
    fi

    # Install requirements
    if [[ -f "$node_path/requirements.txt" ]]; then
        echo "📦 Installing requirements for $node_name..."
        "$VENV_PATH/bin/uv" pip install --python "$VENV_PATH/bin/python" \
            -r "$node_path/requirements.txt" >/dev/null 2>&1 || true
    fi
    
    # Run install script if present
    if [[ -f "$node_path/install.py" ]]; then
        echo "🔧 Running install.py for $node_name..."
        (cd "$node_path" && "$VENV_PATH/bin/python" install.py >/dev/null 2>&1) || true
    fi
}
export -f install_single_node

setup_custom_nodes() {
    log_step "Setting up custom nodes..."
    
    local nodes_dir="$COMFY_DIR/custom_nodes"
    ensure_dir "$nodes_dir"
    
    # Config lookup order:
    # 1. /config/config.yaml (synced from GitHub at runtime)
    # 2. /templates/{type}/config.yaml (baked in image)
    # 3. Legacy TXT manifests
    local config=""
    
    if file_exists "/config/config.yaml"; then
        config="/config/config.yaml"
        log_info "Using synced config for nodes"
    elif file_exists "/templates/${TEMPLATE_TYPE}/config.yaml"; then
        config="/templates/${TEMPLATE_TYPE}/config.yaml"
        log_info "Using image config for nodes"
    fi
    
    if [[ -n "$config" ]]; then
        install_nodes_from_yaml "$config" "$nodes_dir"
    else
        log_info "Using legacy manifest for nodes"
        install_nodes_from_manifest "$nodes_dir"
    fi
    
    log_success "Custom nodes installation complete"
}

install_nodes_from_yaml() {
    local config="$1"
    local nodes_dir="$2"
    
    # Build list for parallel installation
    local node_list
    node_list=$(mktemp)
    
    yaml_list "$config" "nodes" | while read -r item; do
        local repo branch
        repo=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('repo',''))")
        branch=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin).get('branch','main'))")
        
        if [[ -n "$repo" ]]; then
            echo "$repo $branch $nodes_dir" >> "$node_list"
        fi
    done
    
    if [[ -s "$node_list" ]]; then
        log_info "Installing nodes in parallel (max 10)..."
        cat "$node_list" | xargs -P 10 -n 3 bash -c 'install_single_node "$@"' _ || \
            log_warn "Some nodes failed to install"
    fi
    
    rm -f "$node_list"
}

install_nodes_from_manifest() {
    local nodes_dir="$1"
    local manifest="/workspace/custom_nodes_manifest.txt"
    
    # Initialize from template if needed
    if [[ ! -f "$manifest" ]]; then
        local template_manifest="/manifests/${TEMPLATE_TYPE}_nodes.txt"
        if file_exists "$template_manifest"; then
            cp "$template_manifest" "$manifest"
        elif file_exists "/manifests/base_nodes.txt"; then
            cp "/manifests/base_nodes.txt" "$manifest"
        else
            touch "$manifest"
        fi
    fi
    
    if [[ ! -s "$manifest" ]]; then
        log_info "No custom nodes manifest found"
        return 0
    fi
    
    # Parse manifest and install in parallel
    local node_list
    node_list=$(mktemp)
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ $line =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        
        IFS='|' read -r repo_url branch _ <<< "$line"
        repo_url=$(echo "$repo_url" | xargs)
        branch=$(echo "${branch:-main}" | xargs)
        
        if [[ -n "$repo_url" ]]; then
            echo "$repo_url $branch $nodes_dir" >> "$node_list"
        fi
    done < "$manifest"
    
    if [[ -s "$node_list" ]]; then
        log_info "Installing nodes in parallel (max 10)..."
        cat "$node_list" | xargs -P 10 -n 3 bash -c 'install_single_node "$@"' _ || \
            log_warn "Some nodes failed to install"
    fi
    
    rm -f "$node_list"
}

# Run module
setup_custom_nodes
