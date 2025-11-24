#!/bin/bash

install_node() {
    local repo_url="$1"
    local branch="$2"
    local nodes_dir="$3"
    
    local node_name=$(basename "$repo_url" .git)
    local node_path="$nodes_dir/$node_name"
    
    if [ ! -d "$node_path" ]; then
        echo "⬇️ Cloning $node_name..."
        if ! git clone --depth 1 -b "${branch:-main}" "$repo_url" "$node_path"; then
            echo "❌ Failed to clone $node_name"
            return 1
        fi
        echo "✨ Cloned $node_name"
    else
        echo "✅ $node_name already exists"
    fi

    # Always check for requirements
    if [ -f "$node_path/requirements.txt" ]; then
        # Check if we need to install (simple check: are packages installed?)
        # For now, just install to be safe (uv is fast)
        echo "📦 Verifying reqs for $node_name..."
        /venv/bin/uv pip install --python /venv/bin/python -r "$node_path/requirements.txt" >/dev/null 2>&1
    fi
    
    if [ -f "$node_path/install.py" ]; then
        echo "🔧 Running install script for $node_name..."
        cd "$node_path" && /venv/bin/python install.py >/dev/null 2>&1
    fi
}
export -f install_node

setup_custom_nodes() {
    log_info "🔌 Setting up custom nodes..."
    
    local nodes_manifest="/workspace/custom_nodes_manifest.txt"
    local nodes_dir="/workspace/aiclipse/ComfyUI/custom_nodes"
    
    # Initialize manifest from base if missing
    if [ ! -f "$nodes_manifest" ]; then
        if [ -f "/manifests/base_nodes.txt" ]; then
            cp "/manifests/base_nodes.txt" "$nodes_manifest"
            log_info "Initialized with base nodes manifest"
        else
            touch "$nodes_manifest"
        fi
    fi

    # Smart Merge: Update existing entries and append new ones
    local template_manifest="/manifests/${TEMPLATE_TYPE}_nodes.txt"
    if [ -f "$template_manifest" ]; then
        log_info "Merging template manifest: ${TEMPLATE_TYPE}"
        while IFS= read -r line || [ -n "$line" ]; do
            [[ $line =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            
            # Extract repo URL (first field)
            local repo_url=$(echo "$line" | cut -d'|' -f1 | xargs)
            
            if grep -q "^$repo_url|" "$nodes_manifest"; then
                # Entry exists, check if it needs update
                if ! grep -Fxq "$line" "$nodes_manifest"; then
                    log_info "🔄 Updating manifest entry for $repo_url"
                    # Escape special characters for sed (delimiter is |)
                    # We need to escape /, &, and |
                    local escaped_url=$(echo "$repo_url" | sed 's/[\/&|]/\\&/g')
                    local escaped_line=$(echo "$line" | sed 's/[\/&|]/\\&/g')
                    # Pattern: ^url\|.* (match url followed by pipe and rest of line)
                    # We use | as delimiter, so we must escape the literal pipe in the regex as \|
                    sed -i "s|^$escaped_url\|.*|$escaped_line|" "$nodes_manifest"
                fi
            else
                # New entry, append
                echo "$line" >> "$nodes_manifest"
            fi
        done < "$template_manifest"
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
    done < "$nodes_manifest" | xargs -P 10 -n 3 bash -c 'install_node "$@"' _
    
    log_success "Custom nodes installation complete"
}
