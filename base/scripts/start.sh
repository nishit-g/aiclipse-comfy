#!/bin/bash
# =============================================================================
# AiClipse ComfyUI - Modular Entrypoint
# Version: 2.0.0
# =============================================================================
#
# This script orchestrates the startup sequence by running numbered modules
# from the modules/ directory in order. Each module is self-contained and
# handles one aspect of the setup (environment, SSH, ComfyUI, models, etc.)
#
# Modules are sourced (not executed) so they share state and can use common
# functions from lib/*.sh
#
# =============================================================================

set -euo pipefail

# =============================================================================
# LOAD LIBRARIES
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load logging first (used by all modules)
source "$SCRIPT_DIR/lib/logging.sh"

# Load common utilities and constants
source "$SCRIPT_DIR/lib/common.sh"

# Load YAML parsing
source "$SCRIPT_DIR/lib/yaml.sh"

# =============================================================================
# STARTUP BANNER
# =============================================================================
log_section "🚀 AiClipse ComfyUI v${AICLIPSE_VERSION}"
log_info "Template: ${TEMPLATE_TYPE} v${TEMPLATE_VERSION}"
log_info "GPU: ${GPU_TYPE}"

# =============================================================================
# RUN MODULES
# =============================================================================

# Run all modules in numerical order
for module in "$SCRIPT_DIR"/modules/*.sh; do
    if [[ -f "$module" ]]; then
        module_name=$(basename "$module" .sh)
        log_step "Module: $module_name"
        
        # Source module (shares state, can use lib functions)
        if ! source "$module"; then
            log_error "Module failed: $module_name"
            exit 1
        fi
    fi
done

# =============================================================================
# FALLBACK (if no modules exist, use legacy mode)
# =============================================================================
if [[ ! -d "$SCRIPT_DIR/modules" ]] || [[ -z "$(ls -A "$SCRIPT_DIR/modules" 2>/dev/null)" ]]; then
    log_warn "No modules found, using legacy start sequence..."
    
    # Legacy imports
    source "$SCRIPT_DIR/setup_symlinks.sh"
    source "$SCRIPT_DIR/setup_sync.sh"
    source "$SCRIPT_DIR/setup_models.sh"
    source "$SCRIPT_DIR/setup_services.sh"
    source "$SCRIPT_DIR/setup_nodes.sh"
    
    # Legacy sequence (from original start.sh)
    setup_environment 2>/dev/null || true
    setup_ssh_with_export 2>/dev/null || true
    setup_symlinks
    sync_template_if_needed
    setup_comfyui 2>/dev/null || true
    setup_model_paths
    setup_custom_nodes
    download_models_async
    start_all_services
    start_comfyui_with_custom_args 2>/dev/null || exec "$VENV_PATH/bin/python" "$COMFY_DIR/main.py" --listen 0.0.0.0 --port 8188
fi

# Note: Module 10 (launch) calls exec, so we should not reach here
log_error "Unexpected: reached end of start.sh without launching ComfyUI"
exit 1
