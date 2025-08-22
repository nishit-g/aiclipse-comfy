# AiClipse ComfyUI - Professional Templates for Agencies

> Production-ready ComfyUI containers optimized for agency workflows. Built from proven patterns with multi-GPU support, intelligent model management, and enterprise features.

[![Build Status](https://github.com/yourusername/aiclipse-comfyui/workflows/Build/badge.svg)](https://github.com/yourusername/aiclipse-comfyui/actions)
[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/aiclipse-comfyui)](https://hub.docker.com/r/yourusername/aiclipse-comfyui)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Deploy

### RunPod One-Click Templates

| GPU Type | Template | Features |
|----------|----------|----------|
| **RTX 4090, 4080, 3090** | [`aiclipse-headshots:rtx4090-latest`](https://runpod.io/console/deploy?template=your-template-id) | CUDA 12.4, Optimized PyTorch |
| **RTX 5090** | [`aiclipse-headshots:rtx5090-latest`](https://runpod.io/console/deploy?template=your-template-id) | CUDA 12.8, SageAttention |

### Quick Start
1. **Deploy** using RunPod template above
2. **Access** ComfyUI at `http://pod-ip:8188`
3. **Manage files** at `http://pod-ip:8080` (FileBrowser)
4. **SSH in** for advanced configuration

## 📋 Table of Contents

- [🎯 Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [⚙️ Installation](#️-installation)
- [🔧 Configuration](#-configuration)
- [📦 Model Management](#-model-management)
- [🔌 Custom Nodes](#-custom-nodes)
- [🌐 Network & Access](#-network--access)
- [💻 Development](#-development)
- [🎨 Templates](#-templates)
- [🔒 Security](#-security)
- [📊 Monitoring](#-monitoring)
- [❗ Troubleshooting](#-troubleshooting)
- [🚀 Production](#-production)

## 🎯 Features

### Core Features
- **🎮 Multi-GPU Support** - Optimized for RTX 4090 (CUDA 12.4) & RTX 5090 (CUDA 12.8 + SageAttention)
- **📁 Professional File Management** - FileBrowser, Zasper editor, JupyterLab
- **🔐 Secure SSH Access** - Public key auth with environment export
- **🔗 Smart Symlinks** - User-friendly file structure
- **📦 Model Manifests** - HuggingFace-based model management
- **🔄 Template Versioning** - Automatic sync and updates
- **⚙️ Custom Arguments** - Easy ComfyUI configuration

### Production Features
- **🏥 Health Monitoring** - Built-in health checks and logging
- **🔄 Auto-Recovery** - Service restart and error handling
- **📊 Usage Analytics** - Performance monitoring and metrics
- **🛡️ Enterprise Security** - SSH hardening and access control
- **☁️ Cloud Integration** - R2, S3, GCS storage support
- **🔧 DevOps Ready** - CI/CD pipelines and automation

### Developer Features
- **🐳 Docker Buildx** - Multi-platform builds
- **📝 Template SDK** - Easy custom template creation
- **🔌 Plugin System** - Custom node management
- **🧪 Testing Framework** - Automated validation
- **📚 Documentation** - Comprehensive guides and examples

## 🏗️ Architecture

### Project Structure
```
aiclipse-comfyui/
├── 🏗️ base/                      # Base images
│   ├── common.dockerfile          # Shared foundation
│   ├── rtx4090.dockerfile         # RTX 4090 optimized
│   ├── rtx5090.dockerfile         # RTX 5090 + SageAttention
│   └── scripts/                   # Core functionality
│       ├── start.sh               # Main orchestrator
│       ├── setup_symlinks.sh      # Symlink management
│       ├── setup_sync.sh          # Version sync
│       ├── setup_models.sh        # Model management
│       ├── setup_services.sh      # Service control
│       ├── setup_nodes.sh         # Custom node installer
│       └── download_models.py     # HF downloader
├── 🎨 templates/                  # Use case templates
│   ├── headshots/                 # Portrait & headshot generation
│   │   ├── Dockerfile
│   │   ├── models_manifest.txt
│   │   ├── custom_nodes.txt
│   │   └── workflows/
│   ├── products/                  # Product photography
│   ├── brands/                    # Brand & logo design
│   └── video/                     # Video generation
├── 📦 manifests/                  # Model & node catalogs
│   ├── base_models.txt
│   ├── common_nodes.txt
│   └── node_categories/
├── 🔧 scripts/                    # Build & deployment
│   ├── build.sh                   # Smart build system
│   ├── deploy.sh                  # Deployment automation
│   └── test.sh                    # Validation suite
├── 📖 docs/                       # Documentation
│   ├── templates.md               # Template development
│   ├── custom-nodes.md            # Node management
│   ├── deployment.md              # Production guide
│   └── troubleshooting.md         # Common issues
├── docker-bake.hcl               # Multi-target builds
└── README.md                     # This file
```

### Runtime Structure
```
/workspace/
├── 🔗 ComfyUI/          -> /workspace/aiclipse/ComfyUI/
├── 🔗 models/           -> /workspace/aiclipse/models/
├── 🔗 workflows/        -> /workspace/aiclipse/workflows/
├── 🔗 input/            -> /workspace/aiclipse/ComfyUI/input/
├── 🔗 output/           -> /workspace/aiclipse/ComfyUI/output/
├── 🔗 custom_nodes/     -> /workspace/aiclipse/ComfyUI/custom_nodes/
└── aiclipse/
    ├── ComfyUI/         # Main installation
    ├── models/          # Model storage
    │   ├── checkpoints/
    │   ├── loras/
    │   ├── vae/
    │   ├── controlnet/
    │   └── custom/
    ├── workflows/       # Workflow library
    ├── logs/           # Service logs
    └── temp/           # Temporary files
```

## ⚙️ Installation

### Prerequisites
- Docker with BuildKit support
- 50GB+ available disk space
- NVIDIA GPU with 8GB+ VRAM
- RunPod account (for cloud deployment)

### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/aiclipse-comfyui.git
cd aiclipse-comfyui

# 2. Configure build settings
export REGISTRY="ghcr.io/yourusername"
export VERSION="v1.0.0"

# 3. Build base images
./scripts/build.sh bases

# 4. Build specific template
./scripts/build.sh headshots

# 5. Test locally
docker run -p 8188:8188 -p 8080:8080 \
  ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest
```

### RunPod Deployment

1. **Create Template:**
   - Container Image: `ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest`
   - Environment Variables: [See Configuration](#-configuration)
   - Exposed Ports: `22, 8188, 8080, 8888, 8048`
   - Volume Mount: `/workspace`

2. **Deploy Pod:**
   - Select appropriate GPU type
   - Configure environment variables
   - Attach network volume for persistence
   - Deploy and wait for initialization

3. **Access Services:**
   - ComfyUI: `http://pod-ip:8188`
   - FileBrowser: `http://pod-ip:8080`
   - JupyterLab: `http://pod-ip:8888`
   - SSH: `ssh root@pod-ip -p 22`

## 🔧 Configuration

### Environment Variables

#### Core Configuration
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TEMPLATE_TYPE` | Template identifier | `base` | No |
| `TEMPLATE_VERSION` | Version for sync tracking | `1.0.0` | No |
| `AUTO_SYNC` | Enable template sync | `true` | No |
| `DOWNLOAD_MODELS` | Auto-download models | `true` | No |

#### Authentication & Access
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PUBLIC_KEY` | SSH public key | `""` | Recommended |
| `JUPYTER_TOKEN` | JupyterLab access token | `""` | No |
| `ENABLE_JUPYTER` | Enable JupyterLab | `true` | No |

#### Storage & Models
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HF_TOKEN` | HuggingFace access token | `""` | For private models |
| `MODELS_MANIFEST` | Path to model manifest | `/workspace/models_manifest.txt` | No |
| `STORAGE_PROVIDER` | Cloud storage (r2/s3/gcs) | `""` | No |

#### Performance
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_SAGE_ATTENTION` | Use SageAttention (RTX 5090) | `true` (5090 only) | No |
| `COMFY_ARGS` | Custom ComfyUI arguments | `""` | No |
| `MAX_VRAM_GB` | VRAM limit | Auto-detected | No |

### Custom Arguments

Edit `/workspace/aiclipse/comfyui_args.txt` for custom ComfyUI arguments:

```txt
# Performance optimization
--lowvram
--force-fp16
--use-sage-attention

# Preview settings
--preview-method auto
--preview-size 512

# Advanced options
--disable-xformers
--cpu-vae
```

### SSH Configuration

#### Using SSH Keys (Recommended)
```bash
# Generate key pair
ssh-keygen -t ed25519 -f ~/.ssh/aiclipse_key

# Add public key to environment
PUBLIC_KEY=$(cat ~/.ssh/aiclipse_key.pub)

# Connect
ssh root@pod-ip -p 22 -i ~/.ssh/aiclipse_key
```

#### Using Password
```bash
# Password generated automatically if no PUBLIC_KEY
# Check pod logs for generated password
ssh root@pod-ip -p 22
```

## 📦 Model Management

### Model Manifests

Models are managed through manifest files using the format:
```
repo_id|filename|target_directory
```

#### Example Manifest (`/workspace/models_manifest.txt`)
```txt
# Base checkpoints
runwayml/stable-diffusion-v1-5|v1-5-pruned-emaonly.safetensors|checkpoints
SG161222/Realistic_Vision_V5.1_noVAE|Realistic_Vision_V5.1_fp16-no-ema.safetensors|checkpoints

# ControlNet models
lllyasviel/ControlNet-v1-1|control_v11p_sd15_openpose.pth|controlnet
lllyasviel/ControlNet-v1-1|control_v11p_sd15_canny.pth|controlnet

# VAE models
stabilityai/sd-vae-ft-mse-original|vae-ft-mse-840000-ema-pruned.safetensors|vae

# LoRA models
XpucT/Reliberate|Reliberate_v3.safetensors|loras

# Upscaling models
ai-forever/Real-ESRGAN|RealESRGAN_x4plus.pth|upscale_models
```

### Model Commands

```bash
# Download models from manifest
/venv/bin/python /scripts/download_models.py \
  --manifest /workspace/models_manifest.txt \
  --models-dir /workspace/aiclipse/models

# Monitor download progress
tail -f /workspace/aiclipse/logs/models.log

# Check model status
ls -la /workspace/aiclipse/models/*/
```

### Model Organization

```
/workspace/aiclipse/models/
├── checkpoints/          # Main SD models
├── vae/                 # VAE models
├── loras/               # LoRA adaptations
├── controlnet/          # ControlNet models
├── clip/                # CLIP models
├── upscale_models/      # Upscaling models
├── embeddings/          # Textual inversions
└── custom/              # Custom model categories
```

### Private Models

For private HuggingFace models:

```bash
# Set HuggingFace token
export HF_TOKEN="hf_your_token_here"

# Or add to environment variables in RunPod
HF_TOKEN=hf_your_token_here
```

## 🔌 Custom Nodes

### Node Management System

AiClipse includes a comprehensive custom node management system that handles installation, dependencies, and updates automatically.

#### Custom Nodes Manifest

Create `/workspace/custom_nodes_manifest.txt`:

```txt
# Format: repo_url|branch|category|description
https://github.com/Gourieff/comfyui-reactor-node|main|face|Face swapping and enhancement
https://github.com/ltdrdata/ComfyUI-Impact-Pack|main|segmentation|Advanced segmentation tools
https://github.com/Fannovel16/comfyui_controlnet_aux|main|controlnet|ControlNet preprocessors
https://github.com/rgthree/rgthree-comfy|main|ui|UI enhancements and utilities
https://github.com/pythongosssss/ComfyUI-Custom-Scripts|main|scripts|Custom script collection
https://github.com/WASasquatch/was-node-suite-comfyui|main|utility|WAS node suite
https://github.com/cubiq/ComfyUI_IPAdapter_plus|main|adapter|IP-Adapter implementations
https://github.com/jags111/efficiency-nodes-comfyui|main|efficiency|Efficiency nodes
https://github.com/kijai/ComfyUI-KJNodes|main|utility|KJ utility nodes
https://github.com/crystian/ComfyUI-Crystools|main|utility|Crystal tools collection
```

#### Node Categories

**Face & Portrait:**
- `comfyui-reactor-node` - Face swapping and enhancement
- `ComfyUI-Impact-Pack` - Advanced segmentation
- `sd-webui-roop` - Face restoration
- `ComfyUI-FaceAnalysis` - Face detection and analysis

**ControlNet & Pose:**
- `comfyui_controlnet_aux` - ControlNet preprocessors
- `ComfyUI-AdvancedControlNet` - Advanced ControlNet features
- `ComfyUI-AnimateDiff-Evolved` - Animation control
- `ComfyUI-Depth-Anything` - Depth estimation

**Image Enhancement:**
- `ComfyUI-UltimateSDUpscale` - Advanced upscaling
- `ComfyUI-SUPIR` - Image restoration
- `ComfyUI-ESRGAN` - Real-ESRGAN upscaling
- `ComfyUI-PhotoMaker` - Photo enhancement

**Video Generation:**
- `ComfyUI-VideoHelperSuite` - Video processing tools
- `ComfyUI-AnimateDiff` - Animation generation
- `ComfyUI-SVD` - Stable Video Diffusion
- `ComfyUI-Frame-Interpolation` - Frame interpolation

**Workflow Enhancement:**
- `rgthree-comfy` - UI improvements
- `ComfyUI-Custom-Scripts` - Workflow scripts
- `efficiency-nodes-comfyui` - Efficiency tools
- `ComfyUI-Manager` - Node management (pre-installed)

**Text & Language:**
- `ComfyUI-CLIP-Interrogator` - Image to text
- `ComfyUI-Florence2` - Vision-language model
- `ComfyUI-Text-Generation` - Text generation
- `ComfyUI-Prompt-Tools` - Prompt utilities

### Node Installation Commands

#### Automatic Installation (Recommended)
```bash
# Install from manifest
/venv/bin/python /scripts/setup_nodes.py \
  --manifest /workspace/custom_nodes_manifest.txt \
  --comfyui-dir /workspace/ComfyUI

# Install specific category
/venv/bin/python /scripts/setup_nodes.py \
  --category face \
  --comfyui-dir /workspace/ComfyUI
```

#### Manual Installation
```bash
# Via SSH
cd /workspace/ComfyUI/custom_nodes

# Clone and install node
git clone https://github.com/Gourieff/comfyui-reactor-node
cd comfyui-reactor-node
/venv/bin/pip install -r requirements.txt

# Restart ComfyUI to load new nodes
pkill -f "python main.py"
```

#### Via ComfyUI Manager
1. Open ComfyUI web interface
2. Click **Manager** button
3. Select **Install Custom Nodes**
4. Search and install desired nodes
5. Restart ComfyUI when prompted

### Node Setup Script

The `setup_nodes.sh` script handles comprehensive node installation:

```bash
#!/bin/bash
# /scripts/setup_nodes.sh

setup_custom_nodes() {
    local manifest_file="/workspace/custom_nodes_manifest.txt"
    local comfyui_dir="/workspace/ComfyUI"
    local nodes_dir="$comfyui_dir/custom_nodes"

    if [ ! -f "$manifest_file" ]; then
        log "📋 No custom nodes manifest found, using template defaults"
        return 0
    fi

    log "🔌 Installing custom nodes from manifest..."

    while IFS='|' read -r repo_url branch category description; do
        # Skip comments and empty lines
        [[ $repo_url =~ ^#.*$ ]] && continue
        [[ -z "$repo_url" ]] && continue

        local node_name=$(basename "$repo_url" .git)
        local node_path="$nodes_dir/$node_name"

        if [ -d "$node_path" ]; then
            log "✅ $node_name already installed"
            continue
        fi

        log "📦 Installing $node_name ($category)..."

        # Clone repository
        if git clone --depth 1 -b "${branch:-main}" "$repo_url" "$node_path"; then
            # Install requirements if present
            if [ -f "$node_path/requirements.txt" ]; then
                log "📋 Installing requirements for $node_name..."
                /venv/bin/pip install --no-cache-dir -r "$node_path/requirements.txt" || {
                    log "⚠️ Failed to install requirements for $node_name"
                }
            fi

            # Run install script if present
            if [ -f "$node_path/install.py" ]; then
                log "🔧 Running install script for $node_name..."
                cd "$node_path"
                /venv/bin/python install.py || {
                    log "⚠️ Install script failed for $node_name"
                }
                cd "$comfyui_dir"
            fi

            log "✅ Installed $node_name"
        else
            log "❌ Failed to clone $node_name from $repo_url"
        fi

    done < "$manifest_file"

    log "🎉 Custom nodes installation complete"
}
```

### Node Troubleshooting

#### Common Issues

**Import errors:**
```bash
# Check Python path
cd /workspace/ComfyUI/custom_nodes/problem-node
/venv/bin/python -c "import sys; print(sys.path)"

# Reinstall requirements
/venv/bin/pip install --force-reinstall -r requirements.txt
```

**Missing dependencies:**
```bash
# Install common dependencies
/venv/bin/pip install opencv-python pillow numpy torch torchvision

# For specific nodes requiring system packages
apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0
```

**Node not appearing:**
```bash
# Refresh ComfyUI
# Press F5 in browser or restart ComfyUI
pkill -f "python main.py"

# Check ComfyUI logs
tail -f /workspace/aiclipse/logs/comfyui.log
```

#### Performance Optimization

**For RTX 4090:**
```txt
# Add to comfyui_args.txt for memory optimization
--lowvram
--normalvram
--cpu-vae
```

**For RTX 5090:**
```txt
# Optimize for maximum performance
--use-sage-attention
--force-fp16
--preview-method auto
```

### Custom Node Development

#### Creating Custom Nodes

1. **Basic node structure:**
```python
# custom_nodes/my_custom_node/__init__.py
from .my_node import MyCustomNode

NODE_CLASS_MAPPINGS = {
    "MyCustomNode": MyCustomNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyCustomNode": "My Custom Node"
}
```

2. **Node implementation:**
```python
# custom_nodes/my_custom_node/my_node.py
class MyCustomNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "AiClipse/Custom"

    def process(self, image, strength):
        # Your processing logic here
        return (processed_image,)
```

3. **Requirements file:**
```txt
# custom_nodes/my_custom_node/requirements.txt
opencv-python>=4.5.0
pillow>=8.0.0
numpy>=1.21.0
```

#### Testing Custom Nodes

```bash
# Test node loading
cd /workspace/ComfyUI
/venv/bin/python -c "
import sys
sys.path.append('custom_nodes/my_custom_node')
from my_node import MyCustomNode
print('Node loaded successfully')
"

# Test in ComfyUI
# Load a workflow and check if node appears in node menu
```

## 🌐 Network & Access

### Port Configuration

| Port | Service | Description | Access |
|------|---------|-------------|---------|
| `8188` | ComfyUI | Main web interface | Public |
| `8080` | FileBrowser | File management | Public |
| `8888` | JupyterLab | Development environment | Token-protected |
| `8048` | Zasper | Code editor | Public |
| `22` | SSH | Terminal access | Key/password |

### Service URLs

```bash
# ComfyUI Interface
http://pod-ip:8188

# FileBrowser (file management)
http://pod-ip:8080

# JupyterLab (development)
http://pod-ip:8888/?token=your-token

# Zasper (code editor)
http://pod-ip:8048

# SSH Access
ssh root@pod-ip -p 22
```

### Network Volume Structure

When using RunPod network volumes:

```
/workspace/
├── aiclipse/           # Main application directory
├── ComfyUI/           # Symlink to aiclipse/ComfyUI
├── models/            # Symlink to aiclipse/models
├── workflows/         # Symlink to aiclipse/workflows
├── input/             # Symlink to ComfyUI/input
├── output/            # Symlink to ComfyUI/output
└── custom_nodes/      # Symlink to ComfyUI/custom_nodes
```

### Cloud Storage Integration

#### Cloudflare R2

```bash
# Environment variables
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET=your_bucket_name
R2_ACCOUNT_ID=your_account_id

# Commands
r2-upload /workspace/output outputs/$(date +%Y%m%d)
r2-download models/shared /workspace/models
```

#### AWS S3

```bash
# Environment variables
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET=your_bucket_name

# Commands
aws s3 sync /workspace/output s3://your-bucket/outputs/
aws s3 sync s3://your-bucket/models/ /workspace/models/
```

## 💻 Development

### Building Custom Templates

1. **Create template directory:**
```bash
mkdir templates/my-template
cd templates/my-template
```

2. **Create Dockerfile:**
```dockerfile
ARG BASE_IMAGE=ghcr.io/yourusername/aiclipse-base-rtx4090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="my-template"
ENV TEMPLATE_VERSION="1.0.0"

# Copy template files
COPY models_manifest.txt /manifests/my_template_models.txt
COPY custom_nodes.txt /manifests/my_template_nodes.txt
COPY workflows/ /opt/workflows/

# Set manifests
ENV MODELS_MANIFEST="/manifests/my_template_models.txt"
ENV NODES_MANIFEST="/manifests/my_template_nodes.txt"

CMD ["/scripts/start.sh"]
```

3. **Update build configuration:**
```hcl
# Add to docker-bake.hcl
target "my-template-4090" {
    dockerfile = "templates/my-template/Dockerfile"
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-my-template:rtx4090-${VERSION}"]
}
```

### Testing Framework

```bash
# Test all templates
./scripts/test.sh all

# Test specific template
./scripts/test.sh headshots

# Test locally
docker run --rm -p 8188:8188 \
  ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest \
  /scripts/health-check.sh
```

### CI/CD Pipeline

```yaml
# .github/workflows/build.yml
name: Build AiClipse Templates

on:
  push:
    branches: [main, develop]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io/${{ github.repository_owner }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: ./scripts/test.sh

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push
      run: |
        export VERSION=${GITHUB_REF_NAME}
        ./scripts/build.sh all
```

## 🎨 Templates

### Available Templates

#### Headshots Template
**Image:** `aiclipse-headshots:rtx4090-latest` / `aiclipse-headshots:rtx5090-latest`

**Features:**
- Face swapping (Reactor)
- Portrait enhancement (Impact Pack)
- Professional lighting workflows
- Batch processing capabilities

**Models Included:**
- Realistic Vision V5.1
- ControlNet OpenPose/Canny
- Face enhancement LoRAs
- Professional portrait workflows

**Use Cases:**
- Professional headshots
- Corporate portraits
- Social media profiles
- Avatar generation

#### Products Template
**Image:** `aiclipse-products:rtx4090-latest` / `aiclipse-products:rtx5090-latest`

**Features:**
- Product photography workflows
- Background removal/replacement
- Lighting and composition tools
- E-commerce optimization

**Models Included:**
- SDXL Base/Refiner
- Product-specific LoRAs
- Background replacement models
- Enhancement workflows

#### Brands Template
**Image:** `aiclipse-brands:rtx4090-latest` / `aiclipse-brands:rtx5090-latest`

**Features:**
- Logo generation and enhancement
- Brand asset creation
- Style transfer capabilities
- Vector-style outputs

**Models Included:**
- Logo-specific models
- Style transfer networks
- Vector generation tools
- Brand consistency workflows

### Template Comparison

| Feature | Headshots | Products | Brands |
|---------|-----------|----------|---------|
| **Primary Use** | Portrait generation | Product photography | Brand assets |
| **Custom Nodes** | Face tools | Background tools | Style tools |
| **Model Count** | 15+ models | 12+ models | 10+ models |
| **Workflow Count** | 8 workflows | 6 workflows | 5 workflows |
| **GPU Requirement** | 8GB+ VRAM | 12GB+ VRAM | 8GB+ VRAM |

## 🔒 Security

### SSH Hardening

The templates include production-grade SSH security:

```bash
# Automatic SSH configuration
- Key-based authentication (preferred)
- Disabled root password (when using keys)
- Environment variable export for sessions
- Host key generation
- Secure cipher configuration
```

### Access Control

```bash
# Environment-based access control
PUBLIC_KEY="ssh-ed25519 AAAAC3... user@domain"  # SSH key auth
JUPYTER_TOKEN="secure-random-token"              # JupyterLab auth
DISABLE_FILEBROWSER="false"                      # FileBrowser toggle
DISABLE_SSH="false"                              # SSH toggle
```

### Model Security

```bash
# Private model access
HF_TOKEN="hf_your_private_token"  # HuggingFace private repos
MODEL_ENCRYPTION="true"           # Encrypt cached models
SIGNED_MODELS_ONLY="false"        # Only verified models
```

### Network Security

```bash
# Service binding
BIND_ADDRESS="0.0.0.0"    # Public access
# BIND_ADDRESS="127.0.0.1"  # Local only

# Firewall configuration (in production)
ufw allow 8188/tcp  # ComfyUI
ufw allow 8080/tcp  # FileBrowser
ufw allow 22/tcp    # SSH
ufw deny by default
```

### Data Protection

```bash
# Automatic backups
BACKUP_ENABLED="true"
BACKUP_INTERVAL="24h"
BACKUP_DESTINATION="r2://backup-bucket/aiclipse/"

# Encryption at rest
ENCRYPT_WORKSPACE="false"  # Enable for sensitive data
ENCRYPT_MODELS="false"     # Encrypt model cache
```

## 📊 Monitoring

### Health Monitoring

Built-in health checks and monitoring:

```bash
# Service health
curl http://localhost:8188/health    # ComfyUI health
curl http://localhost:8080/health    # FileBrowser health
systemctl status ssh                 # SSH status

# Resource monitoring
nvidia-smi                          # GPU utilization
df -h /workspace                    # Disk usage
free -h                            # Memory usage
```

### Logging System

```bash
# Service logs
tail -f /workspace/aiclipse/logs/comfyui.log      # ComfyUI logs
tail -f /workspace/aiclipse/logs/models.log       # Model downloads
tail -f /workspace/aiclipse/logs/filebrowser.log  # FileBrowser logs
tail -f /workspace/aiclipse/logs/jupyter.log      # JupyterLab logs

# System logs
journalctl -u ssh                   # SSH logs
dmesg | grep -i gpu                # GPU messages
```

### Performance Metrics

```bash
# GPU monitoring
watch -n 1 nvidia-smi

# Memory usage by service
ps aux --sort=-%mem | head -10

# Disk I/O monitoring
iotop -o

# Network monitoring
nethogs
```

### Alerting

```bash
# Set up monitoring alerts (optional)
SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
EMAIL_ALERTS="admin@yourcompany.com"

# Alert thresholds
GPU_TEMP_THRESHOLD=85     # °C
DISK_USAGE_THRESHOLD=90   # %
MEMORY_USAGE_THRESHOLD=95 # %
```

## ❗ Troubleshooting

### Common Issues

#### ComfyUI Won't Start

**Symptoms:** Port 8188 not responding, health check fails

```bash
# Check logs
tail -f /workspace/aiclipse/logs/comfyui.log

# Common causes and fixes
1. **VRAM insufficient:**
   echo "--lowvram" >> /workspace/aiclipse/comfyui_args.txt

2. **Missing models:**
   /venv/bin/python /scripts/download_models.py \
     --manifest /workspace/models_manifest.txt \
     --models-dir /workspace/aiclipse/models

3. **Corrupt installation:**
   rm -rf /workspace/ComfyUI
   # Restart container to reinstall

4. **Custom node errors:**
   cd /workspace/ComfyUI/custom_nodes
   mv problematic_node problematic_node.disabled
   # Restart ComfyUI
```

#### SSH Connection Issues

**Symptoms:** Connection refused, authentication failed

```bash
# Check SSH service
service ssh status

# Restart SSH
service ssh restart

# Check authentication
1. **Key issues:**
   chmod 600 ~/.ssh/authorized_keys
   cat ~/.ssh/authorized_keys  # Verify key format

2. **Permission issues:**
   chmod 700 ~/.ssh
   chown root:root ~/.ssh/authorized_keys

3. **Environment not loaded:**
   source /etc/rp_environment
   echo $PATH  # Verify environment
```

#### Model Download Failures

**Symptoms:** Models not appearing, download errors

```bash
# Check download logs
tail -f /workspace/aiclipse/logs/models.log

# Common fixes
1. **Network issues:**
   ping huggingface.co

2. **Authentication issues:**
   echo $HF_TOKEN  # Verify token

3. **Disk space:**
   df -h /workspace

4. **Manual download:**
   /venv/bin/python /scripts/download_models.py \
     --manifest /workspace/models_manifest.txt \
     --models-dir /workspace/aiclipse/models \
     --token $HF_TOKEN
```

#### Custom Nodes Not Loading

**Symptoms:** Nodes missing from ComfyUI interface

```bash
# Check ComfyUI logs for import errors
grep -i error /workspace/aiclipse/logs/comfyui.log

# Common fixes
1. **Missing dependencies:**
   cd /workspace/ComfyUI/custom_nodes/problem_node
   /venv/bin/pip install -r requirements.txt

2. **Python path issues:**
   export PYTHONPATH="/workspace/ComfyUI:$PYTHONPATH"

3. **Reinstall node:**
   rm -rf /workspace/ComfyUI/custom_nodes/problem_node
   git clone <node_repo> /workspace/ComfyUI/custom_nodes/problem_node

4. **Use ComfyUI Manager:**
   # Access via web interface: Manager -> Install Missing Custom Nodes
```

#### Performance Issues

**Symptoms:** Slow generation, high memory usage

```bash
# Monitor resources
nvidia-smi -l 1        # GPU utilization
htop                   # CPU/memory usage

# Optimization fixes
1. **GPU optimization:**
   echo "--use-sage-attention" >> /workspace/aiclipse/comfyui_args.txt  # RTX 5090
   echo "--lowvram" >> /workspace/aiclipse/comfyui_args.txt             # Low VRAM
   echo "--force-fp16" >> /workspace/aiclipse/comfyui_args.txt          # Faster inference

2. **Memory optimization:**
   echo "--cpu-vae" >> /workspace/aiclipse/comfyui_args.txt
   echo "--normalvram" >> /workspace/aiclipse/comfyui_args.txt

3. **Disk optimization:**
   # Move temp files to faster storage
   export TMPDIR="/tmp"
   # Clean up old files
   find /workspace/aiclipse/temp -type f -mtime +7 -delete
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Set debug environment
export DEBUG=true
export VERBOSE_LOGGING=true

# Restart services with debug
pkill -f "python main.py"
cd /workspace/ComfyUI
/venv/bin/python main.py --listen 0.0.0.0 --port 8188 --verbose

# Check debug logs
tail -f /workspace/aiclipse/logs/debug.log
```

### Support Channels

1. **GitHub Issues:** [Report bugs and request features](https://github.com/yourusername/aiclipse-comfyui/issues)
2. **Community Discord:** Join our support community
3. **Documentation:** [Full documentation site](https://docs.aiclipse.com)
4. **Email Support:** enterprise@aiclipse.com (Enterprise customers)

## 🚀 Production

### Production Deployment

#### Multi-Client Setup

```bash
# Build client-specific images
CLIENT=acme ./scripts/build.sh headshots
CLIENT=corporate ./scripts/build.sh products

# Deploy with client isolation
docker run -d \
  --name acme-headshots \
  -e CLIENT_ID=acme \
  -e WORKSPACE_PREFIX=acme \
  ghcr.io/yourusername/aiclipse-headshots:acme-rtx4090-latest
```

#### Load Balancing

```yaml
# docker-compose.yml for load balancing
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - comfyui-1
      - comfyui-2

  comfyui-1:
    image: ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest
    environment:
      - GPU_DEVICE=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']

  comfyui-2:
    image: ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest
    environment:
      - GPU_DEVICE=1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
```

#### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiclipse-comfyui
spec:
  replicas: 2
  selector:
    matchLabels:
      app: aiclipse-comfyui
  template:
    metadata:
      labels:
        app: aiclipse-comfyui
    spec:
      containers:
      - name: comfyui
        image: ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest
        ports:
        - containerPort: 8188
        env:
        - name: TEMPLATE_TYPE
          value: "headshots"
        resources:
          requests:
            nvidia.com/gpu: 1
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: aiclipse-workspace-pvc
```

### Scaling Strategy

#### Horizontal Scaling

```bash
# Scale based on demand
docker service create \
  --name aiclipse-headshots \
  --replicas 3 \
  --constraint 'node.labels.gpu==nvidia' \
  ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest

# Auto-scaling with Docker Swarm
docker service update \
  --replicas-max-per-node 1 \
  --update-parallelism 1 \
  aiclipse-headshots
```

#### Resource Management

```bash
# Set resource limits
docker run -d \
  --memory=16g \
  --cpus=4 \
  --gpus="device=0" \
  --shm-size=2g \
  ghcr.io/yourusername/aiclipse-headshots:rtx4090-latest
```

### Backup & Recovery

#### Automated Backups

```bash
#!/bin/bash
# /scripts/backup.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/aiclipse_$BACKUP_DATE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup critical data
rsync -av /workspace/aiclipse/workflows/ "$BACKUP_DIR/workflows/"
rsync -av /workspace/aiclipse/custom_nodes/ "$BACKUP_DIR/custom_nodes/"
cp /workspace/models_manifest.txt "$BACKUP_DIR/"
cp /workspace/custom_nodes_manifest.txt "$BACKUP_DIR/"
cp /workspace/aiclipse/comfyui_args.txt "$BACKUP_DIR/"

# Compress backup
tar -czf "/backup/aiclipse_backup_$BACKUP_DATE.tar.gz" -C /backup "aiclipse_$BACKUP_DATE"
rm -rf "$BACKUP_DIR"

# Upload to cloud storage (optional)
if [ -n "$BACKUP_BUCKET" ]; then
    aws s3 cp "/backup/aiclipse_backup_$BACKUP_DATE.tar.gz" "s3://$BACKUP_BUCKET/backups/"
fi

echo "Backup completed: aiclipse_backup_$BACKUP_DATE.tar.gz"
```

#### Recovery Process

```bash
#!/bin/bash
# Recovery from backup

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp/

# Restore files
BACKUP_DIR=$(find /tmp -name "aiclipse_*" -type d | head -1)
rsync -av "$BACKUP_DIR/workflows/" /workspace/aiclipse/workflows/
rsync -av "$BACKUP_DIR/custom_nodes/" /workspace/aiclipse/ComfyUI/custom_nodes/
cp "$BACKUP_DIR/models_manifest.txt" /workspace/
cp "$BACKUP_DIR/comfyui_args.txt" /workspace/aiclipse/

# Restart services
pkill -f "python main.py"
systemctl restart ssh

echo "Recovery completed from $BACKUP_FILE"
```

### Monitoring & Analytics

#### Production Monitoring

```bash
# Prometheus metrics endpoint
curl http://localhost:8188/metrics

# Custom metrics
COMFYUI_REQUESTS_TOTAL counter
COMFYUI_GENERATION_DURATION_SECONDS histogram
COMFYUI_GPU_UTILIZATION_PERCENT gauge
COMFYUI_MEMORY_USAGE_BYTES gauge
```

#### Usage Analytics

```python
# /scripts/analytics.py
import json
import logging
from datetime import datetime

class ComfyUIAnalytics:
    def __init__(self):
        self.log_file = "/workspace/aiclipse/logs/analytics.json"

    def log_generation(self, workflow_type, duration, gpu_memory, success):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "generation",
            "workflow_type": workflow_type,
            "duration_seconds": duration,
            "gpu_memory_mb": gpu_memory,
            "success": success
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
```

### Cost Optimization

#### Resource Efficiency

```bash
# Optimize for cost
1. **Right-size instances:**
   - Use RTX 4090 for most workloads
   - RTX 5090 only for specific use cases

2. **Auto-shutdown:**
   - Configure RunPod auto-stop
   - Implement idle detection

3. **Shared resources:**
   - Use network volumes for model sharing
   - Implement model caching strategies

4. **Batch processing:**
   - Queue multiple requests
   - Process during off-peak hours
```

#### Cost Monitoring

```bash
# Track costs
COST_CENTER="client-acme"
BILLING_PROJECT="headshots-q1-2024"
COST_THRESHOLD_USD=100

# Log resource usage
echo "$(date): GPU Hours: $GPU_HOURS, Cost: $ESTIMATED_COST" >> /workspace/aiclipse/logs/costs.log
```

## 📚 Additional Resources

### Documentation

- **[Template Development Guide](docs/templates.md)** - Creating custom templates
- **[Custom Nodes Guide](docs/custom-nodes.md)** - Node development and management
- **[Production Deployment](docs/deployment.md)** - Enterprise deployment strategies
- **[API Reference](docs/api.md)** - ComfyUI API integration
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions

### Community

- **[GitHub Repository](https://github.com/yourusername/aiclipse-comfyui)** - Source code and issues
- **[Discord Community](https://discord.gg/aiclipse)** - Community support and discussions
- **[YouTube Channel](https://youtube.com/@aiclipse)** - Video tutorials and demonstrations
- **[Blog](https://blog.aiclipse.com)** - Latest updates and best practices

### Support

- **Community Support:** Free support via GitHub issues and Discord
- **Enterprise Support:** Priority support with SLA for enterprise customers
- **Custom Development:** Bespoke template and workflow development services
- **Training:** On-site and remote training for teams

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code of conduct
- Development setup
- Submitting pull requests
- Reporting bugs
- Suggesting features

## 📮 Contact

- **Website:** [https://aiclipse.com](https://aiclipse.com)
- **Email:** hello@aiclipse.com
- **Enterprise:** enterprise@aiclipse.com
- **Twitter:** [@AiClipseAI](https://twitter.com/AiClipseAI)

---

**Built with ❤️ by the AiClipse team**

*Empowering agencies with professional-grade AI workflows*
