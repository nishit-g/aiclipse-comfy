#!/bin/bash
# =============================================================================
# AiClipse Logging Library
# Colored, timestamped logging with section headers and secret masking
# =============================================================================

set -euo pipefail

# =============================================================================
# COLORS
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# CORE LOGGING FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC}  $(date '+%H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC}    $(date '+%H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" >&2
}

# =============================================================================
# ENHANCED LOGGING FUNCTIONS
# =============================================================================

# Section header for major stages
log_section() {
    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Step indicator for progress
log_step() {
    echo -e "${MAGENTA}▶${NC} $1"
}

# Debug logging (only if DEBUG=true)
log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${CYAN}[DEBUG]${NC} $(date '+%H:%M:%S') $1"
    fi
}

# =============================================================================
# SECURITY FUNCTIONS
# =============================================================================

# Mask sensitive data (show first 4 and last 2 chars)
mask_secret() {
    local secret="$1"
    local len=${#secret}
    
    if [[ $len -lt 8 ]]; then
        echo "****"
    else
        echo "${secret:0:4}****${secret: -2}"
    fi
}

# =============================================================================
# EXPORT ALL FUNCTIONS
# =============================================================================
export RED GREEN YELLOW BLUE CYAN MAGENTA BOLD NC
export -f log_info log_success log_warn log_error
export -f log_section log_step log_debug
export -f mask_secret

