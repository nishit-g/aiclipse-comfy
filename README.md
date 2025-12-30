# AiClipse ComfyUI V3

> **Enterprise-grade ComfyUI deployment platform for Modal and RunPod**

[![Modal](https://img.shields.io/badge/Modal-Production%20Ready-blue)](https://modal.com)
[![RunPod](https://img.shields.io/badge/RunPod-Docker%20Ready-purple)](https://runpod.io)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Model Sources](#-model-sources)
- [Adding New Templates](#-adding-new-templates)
- [GPU Configuration](#-gpu-configuration)
- [Environment Variables](#-environment-variables)
- [Modal Deployment](#-modal-deployment)
- [RunPod Deployment](#-runpod-deployment)
- [Performance Tuning](#-performance-tuning)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **⚡ Blazing Fast Downloads** | aria2c with 16 parallel connections (400+ Mbps) |
| **🔧 Config-Driven** | Single `config.yaml` per template |
| **📦 Multi-Source Models** | HuggingFace, Cloudflare R2, CivitAI |
| **🚀 V2 Volumes** | Unlimited files, concurrent writers |
| **🎮 GPU Variants** | RTX 4090/5090, A10G, A100, H100 |
| **🔄 Hot Reload** | Modal serve watches for changes |
| **🔐 Secure Secrets** | Modal secrets for credentials |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Modal CLI
pip install modal
modal setup

# Clone repository
git clone https://github.com/your-org/aiclipse-comfy.git
cd aiclipse-comfy
```

### Modal Deployment

```bash
# 1. Download models to volume (first time only)
modal run v3/templates/qwen-multi-edit/modal/app.py::download_models

# 2. Development mode (hot reload)
modal serve v3/templates/qwen-multi-edit/modal/app.py

# 3. Production deployment
modal deploy v3/templates/qwen-multi-edit/modal/app.py
```

### Access ComfyUI

- **Dev**: `https://YOUR_WORKSPACE--comfy-qwen-multi-edit-serve-dev.modal.run`
- **Prod**: `https://YOUR_WORKSPACE--comfy-qwen-multi-edit-serve.modal.run`

---

## 🏗 Architecture

### Directory Structure

```
aiclipse-comfy/
├── v3/
│   ├── shared/aiclipse/           # Core Library
│   │   ├── __init__.py            # Public API
│   │   ├── config.py              # YAML + env config
│   │   ├── models.py              # Downloader (aria2c, boto3)
│   │   ├── gpu.py                 # GPU configurations
│   │   ├── comfy.py               # ComfyUI launcher
│   │   └── paths.py               # Model path setup
│   │
│   └── templates/
│       └── qwen-multi-edit/       # Template
│           ├── config.yaml        # Template config
│           ├── modal/
│           │   └── app.py         # Modal deployment
│           ├── runpod/
│           │   ├── Dockerfile
│           │   └── entrypoint.py
│           └── workflows/         # ComfyUI workflows
│
├── .env                           # Local credentials
├── .env.template                  # Credential template
├── ARCHITECTURE.md                # Technical docs
└── README.md                      # This file
```

### Core Library Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `config.py` | Configuration loading | `Config.load()`, env overrides |
| `models.py` | Model downloads | `ModelDownloader.download_all()` |
| `gpu.py` | GPU configurations | `get_gpu_config()` |
| `comfy.py` | ComfyUI management | `install_custom_nodes()` |
| `paths.py` | Model path setup | `setup_model_paths()` |

### Data Flow

```
config.yaml
    │
    ▼
┌─────────────────┐
│  Config.load()  │ ◄── Environment Overrides
└─────────────────┘
    │
    ▼
┌─────────────────┐     ┌─────────────────┐
│ ModelDownloader │────▶│  Modal Volume   │
└─────────────────┘     └─────────────────┘
    │                           │
    │ aria2c / boto3            │
    ▼                           ▼
┌─────────────────┐     ┌─────────────────┐
│   HuggingFace   │     │    ComfyUI      │
│   Cloudflare R2 │     │   Web Server    │
└─────────────────┘     └─────────────────┘
```

---

## ⚙️ Configuration

### Template Configuration (`config.yaml`)

```yaml
# Template metadata
name: my-template
version: 1.0.0
description: My ComfyUI template
gpu_requirement: 24GB

# ComfyUI arguments
comfy_args:
  - --highvram
  - --fast fp8_matrix_mult
  - --use-sage-attention
  - --preview-method auto

# Models to download
models:
  - source: huggingface
    repo: org/model-repo
    file: path/to/model.safetensors
    path: checkpoints

# Custom nodes
nodes:
  - repo: https://github.com/org/ComfyUI-Node
    branch: main
```

### Configuration Hierarchy

```
┌─────────────────────────────────────────┐
│  1. Environment Variables (Highest)     │
├─────────────────────────────────────────┤
│  2. config.yaml Values                  │
├─────────────────────────────────────────┤
│  3. Default Values (Lowest)             │
└─────────────────────────────────────────┘
```

---

## 📦 Model Sources

### HuggingFace

```yaml
models:
  - source: huggingface
    repo: Comfy-Org/Qwen-Image-Edit_ComfyUI
    file: split_files/diffusion_models/model.safetensors
    path: diffusion_models
```

**Requirements:**
- Public models: No token needed
- Private/gated models: Set `HF_TOKEN` environment variable

**Download Speed:** 400+ Mbps via aria2c

### Cloudflare R2

```yaml
models:
  - source: r2
    key: loras/my_custom_lora.safetensors
    file: my_custom_lora.safetensors
    path: loras
```

**Requirements:**
Create Modal secret with R2 credentials:

```bash
modal secret create r2-secret \
  R2_ACCESS_KEY_ID=your_key \
  R2_SECRET_ACCESS_KEY=your_secret \
  R2_BUCKET=your_bucket \
  R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
```

### CivitAI

```yaml
models:
  - source: civitai
    model_id: "123456"
    file: model.safetensors
    path: checkpoints
```

> ⚠️ CivitAI support is planned but not yet implemented.

---

## 🆕 Adding New Templates

### Step 1: Create Template Directory

```bash
mkdir -p v3/templates/my-new-template/{modal,runpod,workflows}
```

### Step 2: Create `config.yaml`

```yaml
name: my-new-template
version: 1.0.0
description: Description of your template
gpu_requirement: 24GB

comfy_args:
  - --highvram
  - --preview-method auto

models:
  # Add your models here
  - source: huggingface
    repo: org/model
    file: model.safetensors
    path: checkpoints

nodes:
  # Add custom nodes here
  - repo: https://github.com/org/ComfyUI-Node
```

### Step 3: Copy and Modify `app.py`

```bash
cp v3/templates/qwen-multi-edit/modal/app.py v3/templates/my-new-template/modal/
```

Edit `app.py`:
```python
TEMPLATE_NAME = "my-new-template"
```

### Step 4: Add Workflows

Copy your ComfyUI workflow JSON files to:
```
v3/templates/my-new-template/workflows/
```

### Step 5: Deploy

```bash
# Download models
modal run v3/templates/my-new-template/modal/app.py::download_models

# Serve
modal serve v3/templates/my-new-template/modal/app.py
```

---

## 🎮 GPU Configuration

### Supported GPUs

| Variant | VRAM | CUDA | Modal | RunPod | Best For |
|---------|------|------|-------|--------|----------|
| `a10g` | 24GB | 12.4 | ✅ | ✅ | Standard workloads |
| `rtx4090` | 24GB | 12.4 | ❌ | ✅ | Consumer, FP8 |
| `rtx5090` | 32GB | 12.8 | ❌ | ✅ | Blackwell, newest |
| `a100` | 80GB | 12.4 | ✅ | ✅ | Large models |
| `h100` | 80GB | 12.4 | ✅ | ✅ | Fastest |

### Setting GPU Variant

**Environment Variable:**
```bash
export GPU_VARIANT=a100
```

**In `app.py`:**
```python
GPU_VARIANT = os.environ.get("GPU_VARIANT", "a10g")
```

### GPU-Specific Optimizations

```python
from aiclipse.gpu import get_gpu_config

gpu = get_gpu_config("rtx4090")
print(gpu.supports_fp8)           # True
print(gpu.supports_sage_attention) # True
print(gpu.get_comfy_args())       # ['--fast fp8_matrix_mult', ...]
```

---

## 🔐 Environment Variables

### Core Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TEMPLATE_NAME` | Template identifier | Auto-set |
| `GPU_VARIANT` | GPU type (`a10g`, `a100`, etc.) | Optional |
| `COMFY_ARGS` | Override ComfyUI args | Optional |
| `SKIP_MODEL_DOWNLOAD` | Skip model downloads | Optional |

### Model Download Credentials

| Variable | Description | When Needed |
|----------|-------------|-------------|
| `HF_TOKEN` | HuggingFace token | Private/gated models |
| `R2_ACCESS_KEY_ID` | R2 access key | R2 models |
| `R2_SECRET_ACCESS_KEY` | R2 secret | R2 models |
| `R2_BUCKET` | R2 bucket name | R2 models |
| `R2_ENDPOINT` | R2 endpoint URL | R2 models |

### RunPod-Specific

| Variable | Description | Default |
|----------|-------------|---------|
| `PUBLIC_KEY` | SSH public key | Optional |
| `SSH_PASSWORD` | SSH password | Auto-generated |
| `ENABLE_JUPYTER` | Enable JupyterLab | `false` |
| `JUPYTER_TOKEN` | Jupyter auth token | Empty |

---

## ☁️ Modal Deployment

### Image Layers

```
┌──────────────────────────────────────────────────┐
│  template_image                                  │
│  - Config, workflows, aiclipse library           │
├──────────────────────────────────────────────────┤
│  comfy_image                                     │
│  - ComfyUI via comfy-cli (cached)                │
├──────────────────────────────────────────────────┤
│  base_image                                      │
│  - Python 3.12, system deps, pip packages        │
└──────────────────────────────────────────────────┘
```

### Volumes

| Volume | Path | Purpose |
|--------|------|---------|
| `aiclipse-models-v2` | `/models` | Model storage |
| `aiclipse-outputs-v2` | `/outputs` | Generated images |

### Modal Secrets

```bash
# HuggingFace (for private models)
modal secret create huggingface-secret HF_TOKEN=hf_xxx

# R2 (for custom models)
modal secret create r2-secret \
  R2_ACCESS_KEY_ID=xxx \
  R2_SECRET_ACCESS_KEY=xxx \
  R2_BUCKET=xxx \
  R2_ENDPOINT=xxx
```

### Functions

| Function | Purpose | Command |
|----------|---------|---------|
| `download_models` | Download models | `modal run app.py::download_models` |
| `serve` | Web server | Auto-started |
| `health` | Health check | GET `/health` |

### Deployment Options

```python
@app.function(
    gpu="A10G",              # GPU type
    memory=32768,            # 32GB RAM
    timeout=3600,            # 1 hour
    max_containers=1,        # Concurrent instances
    scaledown_window=300,    # 5 min keep-warm
)
```

---

## 🐳 RunPod Deployment

### Build Image

```bash
docker build \
  --build-arg GPU_VARIANT=rtx4090 \
  -f v3/templates/qwen-multi-edit/runpod/Dockerfile \
  -t ghcr.io/your-org/comfy-qwen:latest \
  .
```

### Push to Registry

```bash
docker push ghcr.io/your-org/comfy-qwen:latest
```

### RunPod Pod Configuration

| Setting | Recommended |
|---------|-------------|
| **GPU** | RTX 4090 / A100 |
| **Container Image** | `ghcr.io/your-org/comfy-qwen:latest` |
| **Volume Mount** | `/runpod-volume` |
| **Exposed Ports** | 8188 (ComfyUI), 22 (SSH), 8888 (Jupyter) |

### Environment Variables

```bash
PUBLIC_KEY="ssh-rsa AAAA..."
ENABLE_JUPYTER=true
SKIP_MODEL_DOWNLOAD=false
```

---

## ⚡ Performance Tuning

### Download Optimization

| Setting | Value | Impact |
|---------|-------|--------|
| aria2c connections | 16 | Saturates bandwidth |
| Parallel files | 4 | Multiple simultaneous |
| Retry count | 3 | Resilience |

### ComfyUI Optimization

```yaml
comfy_args:
  - --highvram              # Keep models in GPU
  - --fast fp8_matrix_mult  # FP8 on RTX 40/50
  - --fast autotune         # PyTorch autotuner
  - --use-sage-attention    # INT8 attention
```

### Cold Start Reduction

| Strategy | Impact | Status |
|----------|--------|--------|
| V2 Volumes | Faster mounts | ✅ Implemented |
| comfy-cli | Pre-baked ComfyUI | ✅ Implemented |
| Memory Snapshots | 3-5x faster | ❌ TODO |
| GPU Fallbacks | Availability | ❌ TODO |

---

## 🔧 Troubleshooting

### Models Not Loading

```bash
# Check volume contents
modal volume ls aiclipse-models-v2

# Verify model paths
modal volume ls aiclipse-models-v2 diffusion_models/
```

### R2 Download Fails

1. Verify secret exists:
   ```bash
   modal secret list
   ```

2. Check credentials:
   ```bash
   # Test locally
   python -c "
   import boto3
   s3 = boto3.client('s3', 
     endpoint_url='YOUR_ENDPOINT',
     aws_access_key_id='YOUR_KEY',
     aws_secret_access_key='YOUR_SECRET'
   )
   print(s3.list_objects_v2(Bucket='YOUR_BUCKET'))
   "
   ```

### ComfyUI Errors

```bash
# View logs
modal logs -f

# Check health endpoint
curl https://YOUR_WORKSPACE--comfy-xxx-health.modal.run
```

### GPU Out of Memory

Adjust `comfy_args` in `config.yaml`:
```yaml
comfy_args:
  - --lowvram    # Offload to RAM
  - --cpu-vae    # VAE on CPU
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

**Code Style:**
- Python: Black formatter
- YAML: 2-space indent
- Docs: Clear, concise, with examples
