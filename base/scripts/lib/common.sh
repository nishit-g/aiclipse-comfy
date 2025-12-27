#!/bin/bash
# =============================================================================
# AiClipse Common Library
# Core constants and utilities shared across all scripts
# =============================================================================

set -euo pipefail

# =============================================================================
# VERSION
# =============================================================================
export AICLIPSE_VERSION="2.0.0"

# =============================================================================
# PATHS
# =============================================================================
export WORKSPACE="${WORKSPACE_DIR:-/workspace/aiclipse}"
export COMFY_DIR="${WORKSPACE}/ComfyUI"
export MODELS_DIR="${WORKSPACE}/models"
export LOGS_DIR="${WORKSPACE}/logs"
export WORKFLOWS_DIR="${WORKSPACE}/workflows"
export VENV_PATH="/venv"
export SCRIPTS_DIR="/scripts"

# =============================================================================
# TEMPLATE INFO
# =============================================================================
export TEMPLATE_VERSION="${TEMPLATE_VERSION:-1.0.0}"
export TEMPLATE_TYPE="${TEMPLATE_TYPE:-base}"
export GPU_TYPE="${GPU_TYPE:-auto}"

# =============================================================================
# CONFIG REPO (for auto-update)
# =============================================================================
export CONFIG_REPO="${CONFIG_REPO:-https://github.com/nishit-g/aiclipse-comfy}"
export CONFIG_BRANCH="${CONFIG_BRANCH:-main}"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Create directory if not exists
ensure_dir() {
    local dir="$1"
    [[ -d "$dir" ]] || mkdir -p "$dir"
}

# Check if file exists
file_exists() {
    [[ -f "$1" ]]
}

# Check if directory exists
dir_exists() {
    [[ -d "$1" ]]
}

# Check if boolean is true
is_true() {
    [[ "${1:-false}" == "true" ]]
}

# Check if variable is set and not empty
is_set() {
    [[ -n "${1:-}" ]]
}

# Safe link with backup
safe_link() {
    local link="$1"
    local target="$2"
    
    if [[ -e "$link" && ! -L "$link" ]]; then
        mv "$link" "${link}.bak.$(date +%s)"
        log_info "📦 Backed up: $link"
    fi
    
    ln -sfn "$target" "$link"
}

# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================
export -f ensure_dir file_exists dir_exists is_true is_set safe_link

# =============================================================================
# SOURCE LOGGING (if available and not already loaded)
# =============================================================================
if ! declare -f log_info > /dev/null 2>&1; then
    _COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$_COMMON_DIR/logging.sh" ]]; then
        source "$_COMMON_DIR/logging.sh"
    fi
    unset _COMMON_DIR
fi
