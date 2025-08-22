#!/bin/bash
# scripts/configure.sh - Setup build environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[CONFIG]${NC} $1"
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

# Configuration setup
setup_build_config() {
    log "🔧 Setting up build configuration..."

    # Default configuration
    export REGISTRY="${REGISTRY:-ghcr.io/nishit-g}"
    export VERSION="${VERSION:-latest}"
    export DOCKER_BUILDKIT=1
    export BUILDX_NO_DEFAULT_ATTESTATIONS=1

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log "📝 Creating .env file from template..."
        cp env.template .env
        warn "Please edit .env file with your configuration"
    fi

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
        log "✅ Loaded configuration from .env"
    fi
}

# Docker setup
setup_docker() {
    log "🐳 Setting up Docker environment..."

    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        error "Docker Buildx is not available"
        exit 1
    fi

    # Create buildx builder if needed
    if ! docker buildx inspect aiclipse-builder &> /dev/null; then
        log "🏗️ Creating Docker Buildx builder..."
        docker buildx create --name aiclipse-builder --driver docker-container --bootstrap
        docker buildx use aiclipse-builder
    else
        docker buildx use aiclipse-builder
    fi

    success "Docker environment ready"
}

# GitHub Container Registry setup
setup_ghcr() {
    log "📦 Setting up GitHub Container Registry..."

    if [ -n "$GITHUB_TOKEN" ]; then
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin
        success "Logged into GitHub Container Registry"
    else
        warn "GITHUB_TOKEN not set, skipping GHCR login"
    fi
}

# Validate configuration
validate_config() {
    log "✅ Validating configuration..."

    local errors=0

    # Check required variables
    if [ -z "$REGISTRY" ]; then
        error "REGISTRY not set"
        ((errors++))
    fi

    if [ -z "$VERSION" ]; then
        error "VERSION not set"
        ((errors++))
    fi

    # Check registry format
    if [[ "$REGISTRY" =~ ^ghcr\.io/ ]]; then
        log "✅ Using GitHub Container Registry"
    elif [[ "$REGISTRY" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/ ]]; then
        log "✅ Using custom registry: $REGISTRY"
    else
        error "Invalid registry format: $REGISTRY"
        ((errors++))
    fi

    # Check Docker access
    if ! docker info &> /dev/null; then
        error "Cannot access Docker daemon"
        ((errors++))
    fi

    if [ $errors -gt 0 ]; then
        error "Configuration validation failed with $errors errors"
        exit 1
    fi

    success "Configuration validation passed"
}

# Create directory structure
setup_directories() {
    log "📁 Setting up directory structure..."

    mkdir -p {manifests,docs,tests,.github/workflows}

    # Create manifest directories
    mkdir -p manifests/{base,headshots,products,brands,video}

    success "Directory structure created"
}

# Generate build scripts
generate_scripts() {
    log "📝 Generating build scripts..."

    # Create build wrapper
    cat > scripts/build-wrapper.sh << 'EOF'
#!/bin/bash
# Auto-generated build wrapper

set -e
source scripts/configure.sh

# Setup environment
setup_build_config
setup_docker
validate_config

# Run actual build
exec scripts/build.sh "$@"
EOF

    chmod +x scripts/build-wrapper.sh

    success "Build scripts generated"
}

# Main setup function
main() {
    echo "🚀 AiClipse ComfyUI Build Configuration Setup"
    echo "============================================="

    setup_build_config
    setup_directories
    setup_docker
    validate_config
    generate_scripts

    if [ -n "$1" ] && [ "$1" = "--ghcr" ]; then
        setup_ghcr
    fi

    echo
    success "🎉 Build environment setup complete!"
    echo
    echo "Next steps:"
    echo "1. Edit .env file with your configuration"
    echo "2. Run: ./scripts/build.sh bases"
    echo "3. Run: ./scripts/build.sh headshots"
    echo "4. Deploy your templates!"
    echo
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
