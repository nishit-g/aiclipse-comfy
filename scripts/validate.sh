#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[VALIDATE]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate manifests
validate_manifests() {
    log "🔍 Validating manifest files..."
    local errors=0

    for manifest in manifests/*.txt templates/*/models_manifest.txt templates/*/nodes_manifest.txt; do
        [ -f "$manifest" ] || continue

        log "Checking $manifest..."

        # Use Python script to validate
        local python_cmd="python3"
        if [ -f "/venv/bin/python" ]; then
            python_cmd="/venv/bin/python"
        fi

        if ! $python_cmd base/scripts/download_models.py --manifest "$manifest" --models-dir /tmp/validate --validate-only 2>/dev/null; then
            error "❌ Invalid manifest: $manifest"
            ((errors++))
        else
            success "✅ Valid manifest: $manifest"
        fi
    done

    return $errors
}

# Validate Dockerfiles
validate_dockerfiles() {
    log "🔍 Validating Dockerfiles..."
    local errors=0

    # Check if hadolint is available
    if ! command -v hadolint &> /dev/null; then
        warn "hadolint not found, skipping Dockerfile validation"
        warn "Install with: docker pull hadolint/hadolint"
        return 0
    fi

    for dockerfile in base/*.dockerfile templates/*/Dockerfile; do
        [ -f "$dockerfile" ] || continue

        log "Checking $dockerfile..."

        if hadolint "$dockerfile"; then
            success "✅ Valid Dockerfile: $dockerfile"
        else
            error "❌ Invalid Dockerfile: $dockerfile"
            ((errors++))
        fi
    done

    return $errors
}

# Validate build configuration
validate_build_config() {
    log "🔍 Validating build configuration..."
    local errors=0

    # Check docker-bake.hcl syntax
    if command -v docker &> /dev/null; then
        if docker buildx bake --print &> /dev/null; then
            success "✅ docker-bake.hcl syntax valid"
        else
            error "❌ docker-bake.hcl syntax invalid"
            ((errors++))
        fi
    else
        warn "Docker not available, skipping build config validation"
    fi

    # Check required files exist
    local required_files=(
        "docker-bake.hcl"
        "base/common.dockerfile"
        "base/rtx4090.dockerfile"
        "base/rtx5090.dockerfile"
        "base/scripts/start.sh"
        "base/scripts/setup_models.sh"
        "base/scripts/setup_nodes.sh"
        "base/scripts/setup_services.sh"
        "base/scripts/setup_symlinks.sh"
        "base/scripts/setup_sync.sh"
        "base/scripts/download_models.py"
        "manifests/base_nodes.txt"
        ".env.template"
        "README.md"
    )

    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            success "✅ Found required file: $file"
        else
            error "❌ Missing required file: $file"
            ((errors++))
        fi
    done

    return $errors
}

# Validate template structure
validate_templates() {
    log "🔍 Validating template structure..."
    local errors=0

    for template_dir in templates/*/; do
        [ -d "$template_dir" ] || continue

        local template_name=$(basename "$template_dir")
        log "Checking template: $template_name"

        # Check required template files
        local template_files=(
            "$template_dir/Dockerfile"
            "$template_dir/models_manifest.txt"
            "$template_dir/README.md"
        )

        for file in "${template_files[@]}"; do
            if [ -f "$file" ]; then
                success "✅ Found: $file"
            else
                error "❌ Missing: $file"
                ((errors++))
            fi
        done

        # Check workflows directory
        if [ -d "$template_dir/workflows" ]; then
            local workflow_count=$(find "$template_dir/workflows" -name "*.json" | wc -l)
            if [ "$workflow_count" -gt 0 ]; then
                success "✅ Found $workflow_count workflow(s) in $template_name"
            else
                warn "⚠️ No JSON workflows found in $template_name/workflows/"
            fi
        else
            warn "⚠️ No workflows directory in $template_name"
        fi
    done

    return $errors
}

# Validate environment configuration
validate_environment() {
    log "🔍 Validating environment configuration..."
    local errors=0

    # Check .env.template format
    if [ -f ".env.template" ]; then
        # Look for critical variables
        local critical_vars=(
            "TEMPLATE_TYPE"
            "TEMPLATE_VERSION"
            "DOWNLOAD_MODELS"
            "PUBLIC_KEY"
            "HF_TOKEN"
        )

        for var in "${critical_vars[@]}"; do
            if grep -q "^$var=" ".env.template" || grep -q "^# $var=" ".env.template"; then
                success "✅ Found $var in .env.template"
            else
                error "❌ Missing $var in .env.template"
                ((errors++))
            fi
        done
    else
        error "❌ Missing .env.template"
        ((errors++))
    fi

    return $errors
}

# Validate scripts syntax
validate_scripts() {
    log "🔍 Validating script syntax..."
    local errors=0

    # Check bash scripts
    for script in base/scripts/*.sh scripts/*.sh; do
        [ -f "$script" ] || continue

        if bash -n "$script"; then
            success "✅ Valid bash syntax: $script"
        else
            error "❌ Invalid bash syntax: $script"
            ((errors++))
        fi
    done

    # Check Python scripts
    for script in base/scripts/*.py; do
        [ -f "$script" ] || continue

        if python3 -m py_compile "$script"; then
            success "✅ Valid Python syntax: $script"
        else
            error "❌ Invalid Python syntax: $script"
            ((errors++))
        fi
    done

    return $errors
}

# Main validation function
main() {
    echo "🔍 AiClipse ComfyUI Project Validation"
    echo "======================================"

    local total_errors=0

    # Run all validations
    validate_manifests || ((total_errors += $?))
    echo

    validate_dockerfiles || ((total_errors += $?))
    echo

    validate_build_config || ((total_errors += $?))
    echo

    validate_templates || ((total_errors += $?))
    echo

    validate_environment || ((total_errors += $?))
    echo

    validate_scripts || ((total_errors += $?))
    echo

    # Summary
    echo "======================================"
    if [ $total_errors -eq 0 ]; then
        success "🎉 All validations passed!"
        echo
        echo "✅ Project is ready for deployment"
        exit 0
    else
        error "❌ Validation failed with $total_errors errors"
        echo
        echo "Please fix the errors above before proceeding."
        exit 1
    fi
}

# Run validation if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
