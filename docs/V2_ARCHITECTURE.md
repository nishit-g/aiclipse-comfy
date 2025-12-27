# AiClipse ComfyUI V2 Architecture

> **Design Philosophy:** *Make adding new templates, workflows, and nodes so easy that a junior developer can do it in 5 minutes.*

---

## Quick Start Examples

### Adding a New Workflow (30 seconds)

```bash
# Just drop a JSON file
cp my-workflow.json templates/boomboom/workflows/

# That's it. Next build picks it up automatically.
```

### Adding a New Custom Node (1 minute)

```yaml
# Add one line to templates/boomboom/nodes.yaml
nodes:
  - repo: https://github.com/author/ComfyUI-NewNode
    branch: main  # optional
```

### Creating a New Template (5 minutes)

```bash
./scripts/new-template.sh my-template --base rtx5090

# Creates:
# templates/my-template/
# ├── template.yaml       # All config in ONE file
# ├── models.yaml         # Model manifest
# ├── nodes.yaml          # Node manifest  
# └── workflows/          # Drop JSON files here
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BUILD TIME                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   templates/                                                             │
│   ├── boomboom/                                                         │
│   │   ├── template.yaml      ← Single source of truth                  │
│   │   ├── models.yaml        ← Model definitions                       │
│   │   ├── nodes.yaml         ← Node definitions                        │
│   │   └── workflows/*.json   ← Just drop files here                    │
│   │                                                                      │
│   └── [new-template]/        ← Copy boomboom, edit yaml, done          │
│                                                                          │
│   docker-bake.hcl            ← Auto-discovers templates                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           RUNTIME                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   /scripts/                                                              │
│   ├── entrypoint.sh          ← Orchestrator (< 50 lines)               │
│   ├── lib/                   ← Shared utilities                        │
│   └── plugins/               ← Modular, ordered execution              │
│       ├── 00-init.sh                                                    │
│       ├── 10-network-volume.sh                                         │
│       ├── 20-ssh.sh                                                     │
│       ├── 30-comfyui.sh                                                │
│       ├── 40-nodes.sh                                                  │
│       ├── 50-models.sh                                                 │
│       ├── 60-workflows.sh                                              │
│       ├── 70-services.sh                                               │
│       └── 99-start.sh                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           PERSISTENT STORAGE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   /workspace/aiclipse/       ← THE VAULT (symlinked to network volume) │
│   ├── ComfyUI/               ← Installation                            │
│   ├── models/                ← All models (shared across templates)    │
│   ├── workflows/             ← User's saved workflows                  │
│   ├── output/                ← Generated images                        │
│   └── state/                 ← Runtime state, versions, logs           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Template Structure (Build Time)

### Single File Configuration: `template.yaml`

Every template is defined by ONE file. No hunting through Dockerfiles, env files, or scripts.

```yaml
# templates/boomboom/template.yaml
name: boomboom
version: 2.0.0
description: Flux-Kontext advanced image editing

# Base image selection
base: rtx5090  # or rtx4090, rtx3090

# ComfyUI runtime arguments
comfy_args:
  - --preview-method auto
  - --highvram
  # Template automatically inherits safe defaults

# Feature flags (all optional, smart defaults)
features:
  jupyter: false
  ssh: true
  auto_update: false

# Model and node manifests are separate files for cleaner organization
# They're auto-loaded from same directory
```

### Model Manifest: `models.yaml`

Clean, validated, typed model definitions.

```yaml
# templates/boomboom/models.yaml
models:
  # HuggingFace models
  - source: huggingface
    repo: black-forest-labs/FLUX.1-Kontext-dev
    file: flux1-kontext-dev.safetensors
    path: diffusion_models
    
  # Cloudflare R2 models
  - source: r2
    key: loras/xelios_v12.safetensors
    path: loras
    
  # CivitAI models  
  - source: civitai
    model_id: 12345
    path: checkpoints
    
  # Direct URL (fallback)
  - source: url
    url: https://example.com/model.safetensors
    path: checkpoints
    checksum: sha256:abc123...  # Optional but recommended
```

### Node Manifest: `nodes.yaml`

```yaml
# templates/boomboom/nodes.yaml
nodes:
  # Minimal definition
  - repo: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
  
  # Full definition
  - repo: https://github.com/ltdrdata/ComfyUI-Manager
    branch: main
    required: true  # Fail if install fails
    
  # With specific commit (for reproducibility)
  - repo: https://github.com/cubiq/ComfyUI_IPAdapter_plus
    commit: abc1234
```

### Workflows Directory

```
templates/boomboom/workflows/
├── flux-kontext-basic.json
├── flux-kontext-inpaint.json
└── flux-kontext-style-transfer.json
```

**To add a workflow:** Just drop a `.json` file. Done.

---

## 2. Runtime Architecture

### Entrypoint: Simple Orchestrator

```bash
#!/bin/bash
# /scripts/entrypoint.sh - The ONLY script you need to understand
set -euo pipefail

# Load shared libraries
source /scripts/lib/common.sh
source /scripts/lib/config.sh

# Run all plugins in order
log_info "🚀 Starting AiClipse ComfyUI..."
for plugin in /scripts/plugins/*.sh; do
    plugin_name=$(basename "$plugin" .sh)
    log_info "▶️  Running: $plugin_name"
    source "$plugin" || {
        log_error "Plugin failed: $plugin_name"
        exit 1
    }
done

log_success "✅ All plugins complete. ComfyUI starting..."
```

**Key insight:** Adding new functionality = adding a new numbered file. No code changes needed.

### Plugin System

Each plugin is:
- **Self-contained** — Does one thing
- **Numbered** — Explicit execution order
- **Skippable** — Check conditions at top
- **Logged** — Clear output about what it's doing

```bash
# /scripts/plugins/40-nodes.sh
#!/bin/bash
# Plugin: Custom Node Installation

# Skip condition
if [[ "${SKIP_NODES:-false}" == "true" ]]; then
    log_info "Skipping node installation (SKIP_NODES=true)"
    return 0
fi

# Load node manifest
manifest="/manifests/${TEMPLATE_TYPE}_nodes.yaml"
if [[ ! -f "$manifest" ]]; then
    log_warn "No node manifest found, skipping"
    return 0
fi

# Install nodes (using shared function)
install_nodes_from_yaml "$manifest"
```

### Adding a New Plugin

```bash
# 1. Create the file
cat > /scripts/plugins/45-my-feature.sh << 'EOF'
#!/bin/bash
# Plugin: My New Feature

[[ "${ENABLE_MY_FEATURE:-false}" == "true" ]] || return 0

log_info "Running my feature..."
# Your code here

log_success "My feature complete"
EOF

# 2. That's it. It runs automatically at position 45.
```

---

## 3. Shared Libraries

### `/scripts/lib/common.sh`

```bash
#!/bin/bash
# Core utilities - imported by all scripts

set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
export AICLIPSE_VERSION="2.0.0"
export WORKSPACE="${WORKSPACE_DIR:-/workspace/aiclipse}"
export COMFY_DIR="${WORKSPACE}/ComfyUI"
export MODELS_DIR="${WORKSPACE}/models"
export STATE_DIR="${WORKSPACE}/state"

# ═══════════════════════════════════════════════════════════════
# LOGGING (with colors, exported for subshells)
# ═══════════════════════════════════════════════════════════════
export RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

export -f log_info log_success log_warn log_error

# ═══════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════
ensure_dir() { mkdir -p "$1"; }
file_exists() { [[ -f "$1" ]]; }
is_true() { [[ "${1:-false}" == "true" ]]; }
mask_secret() { 
    local s="$1"
    [[ ${#s} -lt 8 ]] && echo "****" || echo "${s:0:4}...${s: -4}"
}

export -f ensure_dir file_exists is_true mask_secret
```

### `/scripts/lib/yaml.sh`

```bash
#!/bin/bash
# YAML parsing without external dependencies

# Parse simple YAML (covers 90% of use cases)
# Usage: yaml_get "file.yaml" "models[0].repo"
yaml_get() {
    local file="$1" key="$2"
    python3 -c "
import yaml, sys
with open('$file') as f:
    data = yaml.safe_load(f)
keys = '$key'.replace('[', '.').replace(']', '').split('.')
for k in keys:
    if k.isdigit():
        data = data[int(k)]
    else:
        data = data.get(k)
print(data if data else '')
"
}

# Iterate over YAML array
# Usage: yaml_foreach "file.yaml" "nodes" process_node
yaml_foreach() {
    local file="$1" array_key="$2" callback="$3"
    python3 -c "
import yaml, json
with open('$file') as f:
    data = yaml.safe_load(f)
items = data.get('$array_key', [])
for item in items:
    print(json.dumps(item))
" | while read -r item; do
        $callback "$item"
    done
}

export -f yaml_get yaml_foreach
```

### `/scripts/lib/download.sh`

```bash
#!/bin/bash
# Unified download utilities

download_model() {
    local source="$1" identifier="$2" filename="$3" target_dir="$4"
    
    ensure_dir "$target_dir"
    local target="$target_dir/$filename"
    
    [[ -f "$target" ]] && { log_info "✅ Already exists: $filename"; return 0; }
    
    log_info "⬇️  Downloading: $filename"
    
    case "$source" in
        huggingface|hf)
            download_huggingface "$identifier" "$filename" "$target"
            ;;
        r2|cloudflare)
            download_r2 "$identifier" "$target"
            ;;
        civitai)
            download_civitai "$identifier" "$target"
            ;;
        url)
            download_url "$identifier" "$target"
            ;;
        *)
            log_error "Unknown source: $source"
            return 1
            ;;
    esac
}

download_huggingface() {
    local repo="$1" filename="$2" target="$3"
    python3 -c "
from huggingface_hub import hf_hub_download
import os
hf_hub_download(
    repo_id='$repo',
    filename='$filename',
    local_dir='$(dirname "$target")',
    token=os.environ.get('HF_TOKEN'),
    local_dir_use_symlinks=False
)
"
}

# ... other download functions ...

export -f download_model download_huggingface
```

---

## 4. Extensibility Patterns

### Pattern 1: Drop-in Workflows

```
# To add workflows:
templates/my-template/workflows/
├── existing-workflow.json
└── NEW-workflow.json       ← Just add file, done
```

The `60-workflows.sh` plugin automatically:
1. Scans `/opt/workflows/*.json`
2. Copies to `$WORKSPACE/workflows/`
3. Registers with ComfyUI

### Pattern 2: Declarative Nodes

```yaml
# nodes.yaml - Add one line for new node
nodes:
  - repo: https://github.com/new-author/ComfyUI-NewNode
    # That's it. Installed on next container start.
```

### Pattern 3: Plugin Extensions

```bash
# Add /scripts/plugins/55-my-integration.sh
# Runs automatically between models (50) and workflows (60)
```

### Pattern 4: Environment Overrides

```bash
# Any config can be overridden at runtime
docker run -e COMFY_ARGS="--lowvram" ...
docker run -e SKIP_MODELS=true ...  # For debugging
docker run -e EXTRA_NODES="https://github.com/..." ...
```

---

## 5. Directory Structure (Final)

```
aiclipse-comfy/
├── base/
│   ├── common.dockerfile          # Base image (Python, CUDA, system deps)
│   ├── rtx4090.dockerfile         # 4090-specific (PyTorch, xformers)
│   ├── rtx5090.dockerfile         # 5090-specific (CUDA 12.8, SageAttention)
│   └── scripts/
│       ├── entrypoint.sh          # Main entry (< 30 lines)
│       ├── lib/
│       │   ├── common.sh          # Constants, logging, utilities
│       │   ├── config.sh          # Config loading/validation
│       │   ├── yaml.sh            # YAML parsing
│       │   ├── download.sh        # Model downloading
│       │   └── security.sh        # Input validation
│       └── plugins/
│           ├── 00-init.sh         # Environment setup
│           ├── 10-network-volume.sh # Mount/symlink network storage
│           ├── 20-ssh.sh          # SSH configuration
│           ├── 30-comfyui.sh      # Install/update ComfyUI
│           ├── 40-nodes.sh        # Install custom nodes
│           ├── 50-models.sh       # Download models
│           ├── 60-workflows.sh    # Copy workflows
│           ├── 70-services.sh     # JupyterLab etc
│           └── 99-start.sh        # Start ComfyUI
│
├── templates/
│   ├── boomboom/
│   │   ├── template.yaml          # Template configuration
│   │   ├── models.yaml            # Model manifest
│   │   ├── nodes.yaml             # Node manifest
│   │   ├── workflows/             # Workflow JSON files
│   │   └── README.md              # Template documentation
│   │
│   └── [new-template]/            # Same structure
│
├── scripts/
│   ├── new-template.sh            # Create new template scaffold
│   ├── build.sh                   # Build images
│   └── validate.sh                # Validate manifests
│
├── docker-bake.hcl                # Auto-discovers templates
├── docs/
│   ├── V2_ARCHITECTURE.md         # This document
│   ├── ADDING_TEMPLATES.md        # How to add templates
│   └── ADDING_NODES.md            # How to add nodes
│
└── .github/
    └── workflows/
        └── build.yml              # CI/CD
```

---

## 6. Build System

### Auto-Discovery in `docker-bake.hcl`

```hcl
# Automatically generates targets for all templates
variable "TEMPLATES" {
  default = ["boomboom", "qwen-multi-edit", "sd15-basic"]
}

variable "GPU_TYPES" {
  default = ["rtx4090", "rtx5090"]
}

# Dynamic target generation
target "template" {
  matrix = {
    template = TEMPLATES
    gpu = GPU_TYPES
  }
  name = "${template}-${gpu}"
  dockerfile = "templates/${template}/Dockerfile"
  contexts = {
    base = "target:base-${gpu}"
  }
  tags = ["${REGISTRY}/aiclipse-${template}:${gpu}-${VERSION}"]
}
```

### Template Dockerfile (Generated)

```dockerfile
# templates/boomboom/Dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Copy configuration (YAML files)
COPY template.yaml models.yaml nodes.yaml /config/

# Copy workflows
COPY workflows/ /opt/workflows/

# Set template identity
ENV TEMPLATE_TYPE="boomboom"
ENV TEMPLATE_VERSION="2.0.0"

# Scripts are inherited from base image
CMD ["/scripts/entrypoint.sh"]
```

---

## 7. Adding Things (Cheat Sheet)

| Add This | Do This | Rebuild Needed? |
|----------|---------|-----------------|
| **Workflow** | Drop `.json` in `templates/X/workflows/` | ✅ Yes |
| **Node** | Add line to `templates/X/nodes.yaml` | ✅ Yes |
| **Model** | Add entry to `templates/X/models.yaml` | ✅ Yes |
| **Template** | Run `./scripts/new-template.sh name` | ✅ Yes |
| **Plugin** | Add `.sh` to `base/scripts/plugins/` | ✅ Yes |
| **Runtime Node** | Set `EXTRA_NODES` env var | ❌ No |
| **Runtime Model** | Upload to R2, trigger download | ❌ No |

---

## 8. Configuration Priority

```
1. Environment Variables     (highest - runtime override)
2. template.yaml             (template-specific)
3. base/config/defaults.yaml (base defaults)
4. Hardcoded fallbacks       (lowest - code constants)
```

Example:
```bash
# In template.yaml
comfy_args: ["--highvram"]

# Override at runtime
docker run -e COMFY_ARGS="--lowvram" ...  # Uses --lowvram
```

---

## 9. Security Model

| Layer | Protection |
|-------|------------|
| **Build** | No secrets in images |
| **Runtime** | Secrets via env vars only |
| **Execution** | ComfyUI runs as `comfy` user |
| **Setup** | Root for system config only |
| **Logs** | Secrets masked in output |

```bash
# plugins/00-init.sh
# Setup phase - runs as root
setup_system_config

# plugins/99-start.sh  
# Execution phase - drops to comfy user
exec gosu comfy /venv/bin/python main.py $COMFY_ARGS
```

---

## 10. Migration from V1

```bash
# 1. Convert old manifests to YAML
./scripts/migrate-manifests.sh

# 2. Move scripts to plugins
./scripts/migrate-scripts.sh

# 3. Test
./scripts/validate.sh

# 4. Build
./scripts/build.sh all
```

---

## 11. Model Baking Strategy

### The Problem

Runtime model downloads = **20+ minute cold starts**. UnAcceptable for:
- Serverless (pays for idle GPU time during download)
- Production SLAs
- User experience

### The Solution: Baked vs Runtime Models

```yaml
# templates/boomboom/models.yaml
models:
  # BAKED: Downloaded at build time, in Docker image
  # Pros: Instant start, guaranteed available
  # Cons: Larger image, rebuild to update
  - source: huggingface
    repo: black-forest-labs/FLUX.1-Kontext-dev
    file: flux1-kontext-dev.safetensors
    path: diffusion_models
    bake: true              # ← This model is in the image
    
  # RUNTIME: Downloaded at container start
  # Pros: Smaller image, easy to update
  # Cons: Slow first boot, needs network
  - source: r2
    key: loras/custom-style.safetensors
    path: loras
    bake: false             # ← Downloaded at runtime (default)
    
  # OPTIONAL: Only download if flag is set
  - source: civitai
    model_id: 12345
    path: checkpoints
    optional: true          # ← Only if INCLUDE_OPTIONAL_MODELS=true
```

### Build-Time Baking

```dockerfile
# templates/boomboom/Dockerfile
FROM ${BASE_IMAGE}

# Copy config
COPY template.yaml models.yaml nodes.yaml /config/

# Bake models that have bake: true
RUN /scripts/bake-models.sh /config/models.yaml

# This creates /baked-models/ with the baked models
# At runtime, these are symlinked to $MODELS_DIR
```

### Runtime Handling

```bash
# plugins/50-models.sh
# 1. Link baked models (instant)
if [[ -d /baked-models ]]; then
    log_info "Linking baked models..."
    for model in /baked-models/*; do
        ln -sf "$model" "$MODELS_DIR/"
    done
fi

# 2. Download runtime models (slow, but only missing ones)
download_runtime_models
```

### Image Size vs Start Time Trade-off

| Strategy | Image Size | Cold Start | Best For |
|----------|------------|------------|----------|
| All Runtime | ~5GB | 20-40 min | Development |
| Core Baked | ~25GB | 2-5 min | Standard Production |
| All Baked | ~50GB+ | 30 sec | Serverless, Low-Latency |

---

## 12. Local Development Mode

### `docker-compose.dev.yml`

```yaml
# docker-compose.dev.yml - Run locally WITHOUT GPU
version: '3.8'

services:
  comfyui:
    build:
      context: .
      dockerfile: base/common.dockerfile
      target: runtime
    ports:
      - "8188:8188"     # ComfyUI
      - "8888:8888"     # JupyterLab
      - "2222:22"       # SSH
    volumes:
      # Mount source for live editing
      - ./base/scripts:/scripts:ro
      - ./templates:/templates:ro
      
      # Persistent local data
      - comfyui-models:/workspace/aiclipse/models
      - comfyui-output:/workspace/aiclipse/output
      
    environment:
      - DEV_MODE=true
      - SKIP_GPU_CHECK=true
      - DOWNLOAD_MODELS=false    # Use mock models
      - COMFY_ARGS=--cpu         # CPU mode for testing
      - ENABLE_JUPYTER=true
      
    # No GPU in dev mode
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

volumes:
  comfyui-models:
  comfyui-output:
```

### Dev Commands

```bash
# Start local dev environment
make dev

# Which runs:
docker compose -f docker-compose.dev.yml up --build

# Run with GPU (if available)
make dev-gpu

# Validate all templates without building
make validate

# Test a specific plugin
make test-plugin PLUGIN=40-nodes

# Shell into container for debugging
make shell
```

### Makefile

```makefile
# Makefile
.PHONY: dev dev-gpu validate shell build push

# Development
dev:
	docker compose -f docker-compose.dev.yml up --build

dev-gpu:
	docker compose -f docker-compose.dev.yml -f docker-compose.gpu.yml up --build

shell:
	docker compose -f docker-compose.dev.yml exec comfyui bash

# Validation
validate:
	./scripts/validate.sh

lint:
	shellcheck base/scripts/**/*.sh
	python -m flake8 base/scripts/*.py

# Build
build:
	./scripts/build.sh all

build-%:
	./scripts/build.sh $*

# Push
push:
	./scripts/build.sh all --push
```

---

## 13. Versioning Strategy

### Semantic Versioning

```
MAJOR.MINOR.PATCH

2.1.3
│ │ └── Patch: Bug fixes, security patches
│ └──── Minor: New features, backward compatible
└────── Major: Breaking changes
```

### What Gets Versioned

| Component | Version Source | Example |
|-----------|---------------|---------|
| AiClipse Core | `base/VERSION` | `2.1.3` |
| Template | `template.yaml` | `1.0.0` |
| ComfyUI | Pinned commit | `abc1234` |
| Models | Checksums in manifest | `sha256:...` |

### VERSION File

```bash
# base/VERSION
2.1.3
```

### Auto-Update Integration

Your existing auto-update system + versioning:

```bash
# plugins/00-init.sh
check_for_updates() {
    if [[ "${AUTO_UPDATE:-false}" != "true" ]]; then
        return 0
    fi
    
    # Fetch latest version
    local latest=$(curl -sf "$UPDATE_URL/VERSION")
    local current=$(cat /scripts/VERSION)
    
    if version_gt "$latest" "$current"; then
        log_warn "Update available: $current → $latest"
        
        if [[ "${AUTO_UPDATE_APPLY:-false}" == "true" ]]; then
            apply_update "$latest"
        else
            log_info "Set AUTO_UPDATE_APPLY=true to auto-apply"
        fi
    fi
}

# Controlled update with rollback
apply_update() {
    local version="$1"
    
    # Backup current scripts
    cp -r /scripts /scripts.bak
    
    # Download and apply
    if ! download_and_verify "$version"; then
        log_error "Update failed, rolling back..."
        rm -rf /scripts
        mv /scripts.bak /scripts
        return 1
    fi
    
    log_success "Updated to v$version"
    exec /scripts/entrypoint.sh
}
```

### Rollback Strategy

```bash
# scripts/rollback.sh
#!/bin/bash
# Rollback to previous version

PREVIOUS_VERSION=$(cat /workspace/aiclipse/state/previous_version)

if [[ -z "$PREVIOUS_VERSION" ]]; then
    echo "No previous version found"
    exit 1
fi

echo "Rolling back to v$PREVIOUS_VERSION..."
# Pull specific version tag
docker pull ghcr.io/nishit-g/aiclipse-boomboom:v$PREVIOUS_VERSION
```

### Git Tags for Releases

```bash
# Release workflow
git tag -a v2.1.3 -m "Release 2.1.3: Bug fixes"
git push origin v2.1.3

# GitHub Actions builds and pushes:
# - ghcr.io/nishit-g/aiclipse-boomboom:v2.1.3
# - ghcr.io/nishit-g/aiclipse-boomboom:latest
```

---

## 14. ComfyUI API Integration

### API Endpoints (Research Findings)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Queue a workflow for execution |
| `/queue` | GET | Get queue status (running + pending) |
| `/history/{id}` | GET | Get results for a prompt |
| `/view` | GET | Download generated images |
| `/interrupt` | POST | Stop current execution |
| `/upload/image` | POST | Upload input images |
| `/ws` | WebSocket | Real-time progress updates |

### API-Ready Workflow Storage

```
templates/boomboom/workflows/
├── flux-kontext-basic.json       # UI workflow
└── api/
    └── flux-kontext-basic.json   # API-format workflow
```

### Plugin: API Wrapper

```bash
# plugins/75-api.sh - Optional API wrapper service

[[ "${ENABLE_API_WRAPPER:-false}" == "true" ]] || return 0

log_info "Starting API wrapper..."

# Start wrapper that adds:
# - Authentication
# - Rate limiting
# - Structured responses
# - Webhook callbacks
python /scripts/api/wrapper.py \
    --comfy-url http://localhost:8188 \
    --port 8080 \
    --auth-token "${API_AUTH_TOKEN:-}" \
    &
```

### Python SDK Example

```python
# sdk/aiclipse.py
"""
AiClipse ComfyUI SDK

Usage:
    from aiclipse import AiClipse
    
    client = AiClipse("http://your-pod:8188")
    result = client.run_workflow("flux-kontext-basic", {
        "prompt": "A cat wearing a hat",
        "seed": 42
    })
    result.save("output.png")
"""

import requests
import websocket
import json
import uuid
from pathlib import Path

class AiClipse:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client_id = str(uuid.uuid4())
        
    def run_workflow(self, workflow_name: str, inputs: dict) -> "Result":
        """Run a workflow and wait for result."""
        # Load workflow
        workflow = self._get_workflow(workflow_name)
        
        # Apply inputs
        workflow = self._apply_inputs(workflow, inputs)
        
        # Queue prompt
        prompt_id = self._queue_prompt(workflow)
        
        # Wait for completion
        return self._wait_for_result(prompt_id)
        
    def _queue_prompt(self, workflow: dict) -> str:
        """Queue a workflow for execution."""
        response = requests.post(
            f"{self.base_url}/prompt",
            json={
                "prompt": workflow,
                "client_id": self.client_id
            },
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()["prompt_id"]
        
    def _wait_for_result(self, prompt_id: str) -> "Result":
        """Wait for workflow completion via WebSocket."""
        ws_url = self.base_url.replace("http", "ws") + f"/ws?clientId={self.client_id}"
        
        ws = websocket.create_connection(ws_url)
        try:
            while True:
                msg = json.loads(ws.recv())
                if msg["type"] == "executed" and msg["data"]["prompt_id"] == prompt_id:
                    break
                if msg["type"] == "execution_error":
                    raise Exception(msg["data"]["error"])
        finally:
            ws.close()
            
        # Fetch result
        return self._get_history(prompt_id)
```

---

## 15. Enterprise Additions

### Health Check API

```python
# scripts/api/health.py
from flask import Flask, jsonify
import subprocess
import psutil
import torch

app = Flask(__name__)

@app.route("/health")
def health():
    """Comprehensive health check."""
    return jsonify({
        "status": "healthy",
        "version": open("/scripts/VERSION").read().strip(),
        "template": os.environ.get("TEMPLATE_TYPE"),
        "checks": {
            "comfyui": check_comfyui(),
            "gpu": check_gpu(),
            "models": check_models(),
            "disk": check_disk(),
            "memory": check_memory(),
        }
    })

def check_comfyui():
    try:
        r = requests.get("http://localhost:8188/system_stats", timeout=5)
        return {"status": "ok", "queue_size": r.json().get("queue_running", 0)}
    except:
        return {"status": "error", "message": "ComfyUI not responding"}

def check_gpu():
    if not torch.cuda.is_available():
        return {"status": "error", "message": "No GPU"}
    return {
        "status": "ok",
        "name": torch.cuda.get_device_name(0),
        "memory_used": f"{torch.cuda.memory_allocated()/1e9:.1f}GB",
        "memory_total": f"{torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB"
    }

def check_models():
    models_dir = Path("/workspace/aiclipse/models")
    return {
        "status": "ok",
        "count": sum(1 for _ in models_dir.rglob("*.safetensors")),
        "size_gb": sum(f.stat().st_size for f in models_dir.rglob("*")) / 1e9
    }
```

### Metrics (Prometheus)

```python
# scripts/api/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Metrics
INFERENCE_COUNT = Counter('comfyui_inference_total', 'Total inferences', ['workflow', 'status'])
INFERENCE_TIME = Histogram('comfyui_inference_seconds', 'Inference duration', ['workflow'])
GPU_MEMORY = Gauge('gpu_memory_used_bytes', 'GPU memory usage')
QUEUE_SIZE = Gauge('comfyui_queue_size', 'Current queue size')

@app.route("/metrics")
def metrics():
    # Update gauges
    GPU_MEMORY.set(torch.cuda.memory_allocated())
    QUEUE_SIZE.set(get_queue_size())
    return generate_latest()
```

### Request Authentication

```yaml
# template.yaml
features:
  api_auth: true
  api_auth_method: bearer  # or: api_key, basic, oauth2
```

```python
# Middleware
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token or token != os.environ.get("API_TOKEN"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
```

### Webhook Callbacks

```yaml
# When running via API, get notified on completion
POST /api/run
{
  "workflow": "flux-kontext-basic",
  "inputs": {"prompt": "..."},
  "webhook": "https://your-server.com/callback",
  "webhook_events": ["complete", "error", "progress"]
}
```

---

## 16. What's Still Missing (Brutal Honesty)

| Feature | Priority | Effort | Notes |
|---------|----------|--------|-------|
| **Integration Tests** | P1 | Medium | Test workflows actually run |
| **Rate Limiting** | P1 | Low | Prevent abuse |
| **Multi-GPU** | P2 | High | Split workloads across GPUs |
| **Model Hot-Swap** | P2 | Medium | Load/unload models without restart |
| **A/B Testing** | P3 | Medium | Run multiple model versions |
| **Audit Logging** | P3 | Low | Track who ran what |
| **Cost Tracking** | P3 | Medium | GPU hours per workflow |
| **Multi-Region** | P3 | High | Deploy to multiple clouds |

---

## 17. File Structure (Final V2)

```
aiclipse-comfy/
├── base/
│   ├── VERSION                    # Core version
│   ├── common.dockerfile
│   ├── rtx4090.dockerfile
│   ├── rtx5090.dockerfile
│   └── scripts/
│       ├── entrypoint.sh
│       ├── bake-models.sh         # NEW: Build-time model baking
│       ├── lib/
│       │   ├── common.sh
│       │   ├── config.sh
│       │   ├── yaml.sh
│       │   ├── download.sh
│       │   └── security.sh
│       ├── plugins/
│       │   ├── 00-init.sh
│       │   ├── 10-network-volume.sh
│       │   ├── 20-ssh.sh
│       │   ├── 30-comfyui.sh
│       │   ├── 40-nodes.sh
│       │   ├── 50-models.sh
│       │   ├── 60-workflows.sh
│       │   ├── 70-services.sh
│       │   ├── 75-api.sh           # NEW: API wrapper
│       │   ├── 80-health.sh        # NEW: Health endpoint
│       │   └── 99-start.sh
│       └── api/
│           ├── wrapper.py          # NEW: API wrapper
│           ├── health.py           # NEW: Health checks
│           └── metrics.py          # NEW: Prometheus metrics
│
├── sdk/                            # NEW: Python SDK
│   ├── aiclipse/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── models.py
│   ├── setup.py
│   └── README.md
│
├── templates/
│   └── boomboom/
│       ├── template.yaml
│       ├── models.yaml             # Now with bake: true/false
│       ├── nodes.yaml
│       ├── workflows/
│       │   ├── *.json              # UI workflows
│       │   └── api/                # API-format workflows
│       └── README.md
│
├── docker-compose.dev.yml          # NEW: Local development
├── docker-compose.gpu.yml          # NEW: GPU override
├── Makefile                        # NEW: Dev commands
├── CHANGELOG.md                    # NEW: Version history
└── docs/
    ├── V2_ARCHITECTURE.md
    ├── API.md                      # NEW: API documentation
    └── CONTRIBUTING.md             # NEW: How to contribute
```

---

*V2 Enterprise Architecture*  
*Version: 2.0.0 | Date: 2025-12-28*

