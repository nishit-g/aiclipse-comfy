#!/bin/bash

install_node() {
    local repo_url="$1"
    local branch="$2"
    local nodes_dir="$3"
    
    local node_name=$(basename "$repo_url" .git)
    local node_path="$nodes_dir/$node_name"
    
    if [ -d "$node_path" ]; then
        echo "✅ $node_name already installed"
        return 0
    fi
    
    echo "⬇️ Cloning $node_name..."
    if git clone --depth 1 -b "${branch:-main}" "$repo_url" "$node_path" >/dev/null 2>&1; then
        if [ -f "$node_path/requirements.txt" ]; then
            echo "📦 Installing reqs for $node_name..."
            # Use uv for fast installation
            /venv/bin/uv pip install --system -r "$node_path/requirements.txt" >/dev/null 2>&1
        fi
        
        if [ -f "$node_path/install.py" ]; then
            echo "🔧 Running install script for $node_name..."
            cd "$node_path" && /venv/bin/python install.py >/dev/null 2>&1
        fi
        echo "✨ Installed $node_name"
    else
        echo "❌ Failed to clone $node_name"
        return 1
    fi
}
export -f install_node

setup_custom_nodes() {
    log_info "🔌 Setting up custom nodes..."
    
    local nodes_manifest="/workspace/custom_nodes_manifest.txt"
    local nodes_dir="/workspace/aiclipse/ComfyUI/custom_nodes"
    
    if [ ! -f "$nodes_manifest" ] && [ -f "/manifests/base_nodes.txt" ]; then
        cp "/manifests/base_nodes.txt" "$nodes_manifest"
    fi
    
    if [ ! -f "$nodes_manifest" ]; then
        log_info "No custom nodes manifest found."
        return 0
    fi
    
    log_info "🚀 Installing nodes in parallel (Max 10)..."
    
    # Prepare input list for xargs
    # Format: repo_url branch nodes_dir
    local input_list=""
    while IFS= read -r line || [ -n "$line" ]; do
        [[ $line =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        
        IFS='|' read -r repo_url branch category <<< "$line"
        repo_url=$(echo "$repo_url" | xargs)
        branch=$(echo "$branch" | xargs)
        
        if [ -n "$repo_url" ]; then
            echo "$repo_url ${branch:-main} $nodes_dir"
        fi
    done < "$nodes_manifest" | xargs -P 10 -n 3 -I {} bash -c 'install_node "$@"' _ {}
    
    log_success "Custom nodes installation complete"
}
