#!/bin/bash

setup_custom_nodes() {
    log "🔌 Setting up custom nodes..."

    local nodes_manifest="/workspace/custom_nodes_manifest.txt"
    local comfyui_dir="/workspace/aiclipse/ComfyUI"
    local nodes_dir="$comfyui_dir/custom_nodes"

    # Create default manifest if none exists
    if [ ! -f "$nodes_manifest" ] && [ -f "/manifests/base_nodes.txt" ]; then
        cp "/manifests/base_nodes.txt" "$nodes_manifest"
        log "📋 Created default custom nodes manifest"
    fi

    # Skip if no manifest
    if [ ! -f "$nodes_manifest" ]; then
        log "ℹ️ No custom nodes manifest found, skipping"
        return 0
    fi

    log "📦 Installing custom nodes from manifest..."

    # Process each line in manifest - FIXED VERSION
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ $line =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # Parse the line - now properly handling the full line first
        IFS='|' read -r repo_url branch category description <<< "$line"

        # Validate required fields
        if [[ -z "$repo_url" ]]; then
            log "⚠️ Skipping line with empty repo URL: $line"
            continue
        fi

        local node_name=$(basename "$repo_url" .git)
        local node_path="$nodes_dir/$node_name"

        # Check if already installed
        if [ -d "$node_path" ]; then
            log "✅ $node_name already installed"
            continue
        fi

        log "🔧 Installing $node_name (${category:-general})..."

        # Clone repository with error handling
        if git clone --depth 1 -b "${branch:-main}" "$repo_url" "$node_path" 2>/dev/null; then
            cd "$node_path"

            # Install requirements if present
            if [ -f "requirements.txt" ]; then
                log "📋 Installing requirements for $node_name..."
                if ! /venv/bin/pip install --no-cache-dir -r requirements.txt; then
                    log "⚠️ Failed to install requirements for $node_name"
                fi
            fi

            # Run install script if present
            if [ -f "install.py" ]; then
                log "🔧 Running install script for $node_name..."
                if ! /venv/bin/python install.py; then
                    log "⚠️ Install script failed for $node_name"
                fi
            fi

            log "✅ Installed $node_name"
        else
            log "❌ Failed to clone $node_name from $repo_url"
        fi

        cd "$comfyui_dir"

    done < "$nodes_manifest"

    log "🎉 Custom nodes installation complete"
}

# Python version for more robust handling
setup_custom_nodes_python() {
    log "🔌 Setting up custom nodes (Python)..."

    /venv/bin/python3 << 'PYTHON_SCRIPT'
import os
import sys
import subprocess
import urllib.parse
from pathlib import Path

def log(message):
    print(f"[NODES] {message}", flush=True)

def install_custom_nodes():
    nodes_manifest = "/workspace/custom_nodes_manifest.txt"
    comfyui_dir = Path("/workspace/aiclipse/ComfyUI")
    nodes_dir = comfyui_dir / "custom_nodes"

    if not Path(nodes_manifest).exists():
        log("No custom nodes manifest found, skipping")
        return

    nodes_dir.mkdir(exist_ok=True)
    success_count = 0
    error_count = 0

    with open(nodes_manifest, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            try:
                parts = line.split('|')
                if len(parts) < 1 or not parts[0].strip():
                    log(f"Line {line_num}: Invalid format, skipping: {line}")
                    error_count += 1
                    continue

                repo_url = parts[0].strip()
                branch = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "main"
                category = parts[2].strip() if len(parts) > 2 else "general"

                # Extract repo name
                parsed_url = urllib.parse.urlparse(repo_url)
                repo_name = Path(parsed_url.path).stem
                node_path = nodes_dir / repo_name

                if node_path.exists():
                    log(f"✅ {repo_name} already installed")
                    continue

                log(f"🔧 Installing {repo_name} ({category})...")

                # Clone repository
                result = subprocess.run([
                    "git", "clone", "--depth", "1",
                    "-b", branch, repo_url, str(node_path)
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    # Install requirements
                    req_file = node_path / "requirements.txt"
                    if req_file.exists():
                        log(f"📋 Installing requirements for {repo_name}...")
                        req_result = subprocess.run([
                            "/venv/bin/pip", "install", "--no-cache-dir",
                            "-r", str(req_file)
                        ], capture_output=True, text=True)

                        if req_result.returncode != 0:
                            log(f"⚠️ Requirements installation failed for {repo_name}: {req_result.stderr}")

                    # Run install script
                    install_script = node_path / "install.py"
                    if install_script.exists():
                        log(f"🔧 Running install script for {repo_name}...")
                        install_result = subprocess.run([
                            "/venv/bin/python", str(install_script)
                        ], cwd=str(node_path), capture_output=True, text=True)

                        if install_result.returncode != 0:
                            log(f"⚠️ Install script failed for {repo_name}: {install_result.stderr}")

                    log(f"✅ Installed {repo_name}")
                    success_count += 1
                else:
                    log(f"❌ Failed to clone {repo_name}: {result.stderr}")
                    error_count += 1

            except Exception as e:
                log(f"❌ Error processing line {line_num}: {e}")
                error_count += 1

    log(f"🎉 Custom nodes setup complete: {success_count} success, {error_count} errors")

if __name__ == "__main__":
    install_custom_nodes()

PYTHON_SCRIPT

    log "🎉 Custom nodes setup complete"
}
