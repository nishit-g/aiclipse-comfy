# FINAL V2 ARCHITECTURE

> **What we have:** Scripts that work.
> **What we want:** Scripts that are fast, clean, and extensible.

---

## Current State Analysis

### What's Working Well ✅

| Feature | Implementation | Quality |
|---------|----------------|---------|
| **Parallel Model Downloads** | `aria2c -x 16 -s 16 -j 10` | Excellent |
| **Parallel Node Installs** | `xargs -P 10` | Good |
| **Multi-Source Downloads** | HF + R2 + CivitAI | Complete |
| **Logging** | `lib/logging.sh` with colors | Clean |
| **Symlinks** | Robust with backup | Smart |
| **Auto-Update** | Git clone + rsync | Works |

### What Needs Improvement ⚠️

| Issue | Location | Impact |
|-------|----------|--------|
| **No `set -euo pipefail`** | All scripts | Silent failures |
| **Monolithic start.sh** | 249 lines, hard to maintain | Tech debt |
| **TXT manifests** | Hard to add metadata | Limited |
| **Duplicate download logic** | Bash + Python | Confusing |
| **SSH password in logs** | start.sh:166 | Security |
| **No version tracking** | Everywhere | Can't rollback |

---

## V2 Design: Minimal Changes, Maximum Impact

### Principle: **Don't rewrite what works. Fix what's broken.**

```
V1 (Current)                    V2 (Target)
─────────────                   ───────────
start.sh (249 lines)     →      start.sh (orchestrator) + modules/
setup_*.sh (scattered)   →      modules/*.sh (organized)
manifests/*.txt          →      templates/*/config.yaml
lib/logging.sh           →      lib/ (expanded)
```

---

## Directory Structure

```
base/scripts/
├── start.sh                 # MODIFIED: Orchestrates modules
├── lib/
│   ├── logging.sh           # EXISTS: Keep as-is
│   ├── common.sh            # NEW: Constants, utilities
│   ├── yaml.sh              # NEW: YAML parsing
│   └── download.sh          # NEW: Unified download functions
├── modules/
│   ├── 01_environment.sh    # FROM: start.sh:104-145
│   ├── 02_update.sh         # FROM: start.sh:21-58
│   ├── 03_ssh.sh            # FROM: start.sh:148-170
│   ├── 04_symlinks.sh       # FROM: setup_symlinks.sh
│   ├── 05_comfyui.sh        # FROM: start.sh:173-216
│   ├── 06_models.sh         # FROM: setup_models.sh
│   ├── 07_nodes.sh          # FROM: setup_nodes.sh
│   ├── 08_workflows.sh      # FROM: setup_sync.sh
│   ├── 09_services.sh       # FROM: setup_services.sh
│   └── 10_launch.sh         # FROM: start.sh:219-245
└── download_models.py       # EXISTS: Keep (R2 + complex logic)

templates/
└── boomboom/
    ├── Dockerfile           # EXISTS: Keep
    ├── config.yaml          # NEW: Replaces models_manifest.txt etc.
    └── workflows/           # EXISTS: Keep
```

---

## 1. New start.sh (Orchestrator)

```bash
#!/bin/bash
set -euo pipefail

# Load core libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/common.sh"

log_section "🚀 AiClipse ComfyUI v${AICLIPSE_VERSION}"
log_info "Template: ${TEMPLATE_TYPE} | GPU: ${GPU_TYPE:-auto}"

# Run all modules in order
for module in "$SCRIPT_DIR"/modules/*.sh; do
    module_name=$(basename "$module" .sh)
    log_step "Running: $module_name"
    
    # Each module is sourced (not executed) so it shares state
    source "$module" || {
        log_error "Module failed: $module_name"
        exit 1
    }
done

log_success "✅ All modules complete"
```

**Changes from current:**
- Added `set -euo pipefail`
- Loops through modules instead of hardcoded function calls
- Each module is independent and testable

---

## 2. lib/common.sh

```bash
#!/bin/bash
set -euo pipefail

# Version
export AICLIPSE_VERSION="2.0.0"

# Paths (stable across all scripts)
export WORKSPACE="${WORKSPACE_DIR:-/workspace/aiclipse}"
export COMFY_DIR="${WORKSPACE}/ComfyUI"
export MODELS_DIR="${WORKSPACE}/models"
export LOGS_DIR="${WORKSPACE}/logs"
export VENV_PATH="/venv"

# Template info
export TEMPLATE_VERSION="${TEMPLATE_VERSION:-1.0.0}"
export TEMPLATE_TYPE="${TEMPLATE_TYPE:-base}"

# Utilities
ensure_dir() { mkdir -p "$1"; }
file_exists() { [[ -f "$1" ]]; }
dir_exists() { [[ -d "$1" ]]; }
is_true() { [[ "${1:-false}" == "true" ]]; }

# Export for subshells
export -f ensure_dir file_exists dir_exists is_true
```

---

## 3. lib/yaml.sh

```bash
#!/bin/bash

# Parse YAML using Python (always available)
# Usage: yaml_get "config.yaml" ".models[0].repo"
yaml_get() {
    local file="$1"
    local key="$2"
    python3 -c "
import yaml
with open('$file') as f:
    d = yaml.safe_load(f)
# Simple key access (supports dot notation and array indices)
for k in '$key'.lstrip('.').replace('[', '.').replace(']', '').split('.'):
    if k.isdigit():
        d = d[int(k)] if d else None
    else:
        d = d.get(k) if d else None
print(d if d is not None else '')
"
}

# Iterate YAML array as JSON lines
# Usage: yaml_list "config.yaml" "models" | while read -r item; do ... done
yaml_list() {
    local file="$1"
    local key="$2"
    python3 -c "
import yaml, json
with open('$file') as f:
    d = yaml.safe_load(f)
items = d.get('$key', []) if d else []
for item in items:
    print(json.dumps(item))
"
}

export -f yaml_get yaml_list
```

---

## 4. Template config.yaml

Replaces `models_manifest.txt` and `nodes_manifest.txt`:

```yaml
# templates/boomboom/config.yaml
name: boomboom
version: 2.0.0
description: Flux Kontext for advanced image generation
gpu_requirement: 24GB

# ComfyUI arguments
comfy_args:
  - --highvram
  - --preview-method auto

# Models to download
models:
  # Core Flux model
  - source: huggingface
    repo: black-forest-labs/FLUX.1-Kontext-dev
    file: flux1-kontext-dev.safetensors
    path: unet
    
  # VAE
  - source: huggingface
    repo: black-forest-labs/FLUX.1-Kontext-dev
    file: ae.safetensors
    path: vae
    
  # Text encoders
  - source: huggingface
    repo: comfyanonymous/flux_text_encoders
    file: clip_l.safetensors
    path: text_encoders
    
  - source: huggingface
    repo: comfyanonymous/flux_text_encoders
    file: t5xxl_fp8_e4m3fn.safetensors
    path: text_encoders
    
  # R2 models
  - source: r2
    key: loras/v12_xelios_it.safetensors
    file: v12_xelios_it.safetensors
    path: loras

# Custom nodes to install
nodes:
  - repo: https://github.com/ltdrdata/ComfyUI-Manager
  - repo: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
  - repo: https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

**Benefits over TXT:**
- Comments stay with data
- Typed fields (source, repo, file, path)
- Single file per template
- Easy to add metadata (description, requirements)

---

## 5. Module Examples

### modules/06_models.sh

```bash
#!/bin/bash
# Module: Model downloads

setup_model_paths() {
    log_info "Configuring model paths..."
    
    ensure_dir "$MODELS_DIR"
    
    # Symlink ComfyUI/models → persistent storage
    local comfy_models="$COMFY_DIR/models"
    
    if [[ -L "$comfy_models" ]]; then
        log_info "Models already linked"
        return 0
    fi
    
    if [[ -d "$comfy_models" && ! -L "$comfy_models" ]]; then
        log_info "Migrating existing models..."
        rsync -a --ignore-existing "$comfy_models/" "$MODELS_DIR/"
        rm -rf "$comfy_models"
    fi
    
    ln -sfn "$MODELS_DIR" "$comfy_models"
    log_success "Models linked: $comfy_models → $MODELS_DIR"
}

download_models() {
    is_true "$DOWNLOAD_MODELS" || {
        log_info "Skipping downloads (DOWNLOAD_MODELS=false)"
        return 0
    }
    
    local config="/manifests/${TEMPLATE_TYPE}/config.yaml"
    [[ -f "$config" ]] || config="/templates/${TEMPLATE_TYPE}/config.yaml"
    
    if [[ ! -f "$config" ]]; then
        log_warn "No config.yaml found for template"
        return 0
    fi
    
    # Generate aria2c input from YAML
    local aria2_input=$(mktemp)
    generate_aria2_input "$config" "$aria2_input"
    
    if [[ -s "$aria2_input" ]]; then
        log_info "Starting parallel downloads..."
        aria2c -i "$aria2_input" \
            -x 16 -s 16 -j 10 \
            -c --auto-file-renaming=false \
            --console-log-level=warn
    fi
    
    # R2 downloads via Python
    download_r2_models "$config"
    
    rm -f "$aria2_input"
}

generate_aria2_input() {
    local config="$1"
    local output="$2"
    
    yaml_list "$config" "models" | while read -r item; do
        local source=$(echo "$item" | jq -r '.source')
        [[ "$source" == "r2" ]] && continue  # R2 handled separately
        
        local repo=$(echo "$item" | jq -r '.repo')
        local file=$(echo "$item" | jq -r '.file')
        local path=$(echo "$item" | jq -r '.path')
        
        local url="https://huggingface.co/${repo}/resolve/main/${file}"
        
        echo "$url" >> "$output"
        echo "  out=$file" >> "$output"
        echo "  dir=$MODELS_DIR/$path" >> "$output"
        
        if [[ -n "$HF_TOKEN" ]]; then
            echo "  header=Authorization: Bearer $HF_TOKEN" >> "$output"
        fi
    done
}

download_r2_models() {
    local config="$1"
    local r2_manifest=$(mktemp)
    
    # Extract R2 entries
    yaml_list "$config" "models" | while read -r item; do
        local source=$(echo "$item" | jq -r '.source')
        [[ "$source" == "r2" ]] || continue
        
        local key=$(echo "$item" | jq -r '.key')
        local file=$(echo "$item" | jq -r '.file')
        local path=$(echo "$item" | jq -r '.path')
        
        echo "r2|$key|$file|$path" >> "$r2_manifest"
    done
    
    if [[ -s "$r2_manifest" ]]; then
        /venv/bin/python /scripts/download_models.py \
            --manifest "$r2_manifest" \
            --models-dir "$MODELS_DIR"
    fi
    
    rm -f "$r2_manifest"
}

# Run
setup_model_paths
download_models
```

---

## 6. Security Fixes

### modules/03_ssh.sh

```bash
#!/bin/bash
# Module: SSH setup with secure logging

setup_ssh() {
    log_info "Configuring SSH..."
    
    mkdir -p ~/.ssh
    
    # Generate keys
    for type in rsa ecdsa ed25519; do
        local key="/etc/ssh/ssh_host_${type}_key"
        [[ -f "$key" ]] || ssh-keygen -t "$type" -f "$key" -q -N ''
    done
    
    # Authentication
    if [[ -n "${PUBLIC_KEY:-}" ]]; then
        echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        log_success "SSH: Public key authentication configured"
    else
        local pass=$(openssl rand -base64 12)
        echo "root:${pass}" | chpasswd
        
        # SECURITY FIX: Don't log full password
        # Write to secure file instead
        echo "$pass" > /workspace/aiclipse/.ssh_password
        chmod 600 /workspace/aiclipse/.ssh_password
        
        log_info "SSH: Password saved to /workspace/aiclipse/.ssh_password"
    fi
    
    /usr/sbin/sshd
}

setup_ssh
```

---

## 7. Logging Enhancements

### lib/logging.sh (enhanced)

```bash
#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Functions
log_info()    { echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $(date '+%H:%M:%S') $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" >&2; }

# NEW: Section header
log_section() { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}\n"; }

# NEW: Step indicator
log_step() { echo -e "${CYAN}▶${NC} $1"; }

# NEW: Mask sensitive data
mask_secret() {
    local s="$1"
    [[ ${#s} -lt 8 ]] && echo "****" || echo "${s:0:4}****${s: -2}"
}

export -f log_info log_success log_warn log_error log_section log_step mask_secret
```

---

## Implementation Order

| Day | Task | Files |
|-----|------|-------|
| **1** | Add `set -euo pipefail` to all scripts | All `.sh` |
| **1** | Create `lib/common.sh` | New |
| **1** | Create `lib/yaml.sh` | New |
| **2** | Create `modules/` directory structure | New |
| **2** | Extract modules from start.sh | 01-03 |
| **3** | Extract remaining modules | 04-10 |
| **4** | Create `config.yaml` for boomboom | New |
| **4** | Update model download to use YAML | 06_models.sh |
| **5** | Test full flow | Integration |
| **5** | Convert other templates | qwen, sd15 |

---

## What We're NOT Doing

| Feature | Why Not |
|---------|---------|
| Plugin discovery | Numbered modules work fine |
| Feature flags | Env vars are enough |
| Prometheus metrics | No users yet |
| Non-root user | Container complexity |
| Python SDK | Focus on core first |

---

## Success Criteria

- [ ] All scripts have `set -euo pipefail`
- [ ] SSH password not in logs
- [ ] Templates use `config.yaml`
- [ ] Modules load in 10 numbered files
- [ ] Downloads still parallel and fast
- [ ] All 3 templates work
