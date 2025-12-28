# AiClipse ComfyUI - Modal Platform

Enterprise-grade ComfyUI deployment on [Modal](https://modal.com) with config-driven architecture, pre-downloaded models, and memory snapshots for fast cold starts.

---

## 📖 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Commands](#commands)
- [Volumes](#volumes)
- [Performance](#performance)
- [Environment Variables](#environment-variables)
- [Secrets](#secrets)
- [Development](#development)

---

## 🚀 Quick Start

```bash
# 1. Pre-download models to Volume (CPU, cheap)
modal run platform/modal/download.py --template boomboom

# 2. Development mode (hot reload)
modal serve platform/modal/serve.py

# 3. Production deployment
modal deploy platform/modal/serve.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     config.yaml (Source of Truth)               │
│     templates/boomboom/config.yaml - same as RunPod             │
└─────────────────────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│   download.py           │               │   serve.py              │
│   CPU: 4 cores, 8GB     │               │   GPU: L40S/A100        │
│   aria2c: 16×4 parallel │  ──Volume───▶ │   GHCR Image            │
│   ~180 MB/s downloads   │               │   Memory Snapshots      │
└─────────────────────────┘               └─────────────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│   Modal Volume          │               │   ComfyUI Web UI        │
│   aiclipse-models       │               │   Port 8188             │
│   ~50GB pre-downloaded  │               │   start.sh → ComfyUI    │
└─────────────────────────┘               └─────────────────────────┘
```

### Key Design Principles

1. **Config-Driven**: Same `templates/*/config.yaml` as RunPod
2. **Separation of Concerns**: CPU downloads (cheap) vs GPU serving (fast)
3. **Volume Persistence**: Models downloaded once, reused forever
4. **Memory Snapshots**: Fast cold starts with `enable_memory_snapshot=True`
5. **GHCR Images**: Your existing Docker images, no rebuild needed

---

## 📁 File Structure

```
platform/modal/
├── serve.py          # Main GPU server (ComfyUI)
├── download.py       # Enterprise model downloader (aria2c)
├── app.py           # Entry point (re-exports)
├── images.py        # GHCR image definitions
├── __init__.py      # Package exports
├── README.md        # This file
└── config/
    ├── __init__.py
    ├── secrets.py   # Modal Secrets management
    ├── templates.py # Template configuration
    └── volumes.py   # Volume definitions
```

### Core Files

| File | Purpose | Key Features |
|------|---------|--------------|
| `serve.py` | GPU server | `@modal.web_server`, memory snapshots, Volume symlinks |
| `download.py` | Model downloader | aria2c (16×4 parallel), R2 support, HuggingFace |
| `images.py` | Container images | GHCR mapping, GPU mapping |

### Base Layer (Inherited)

```
base/
├── common.dockerfile     # CUDA 12.4 + Python 3.12 + system deps
├── rtx5090.dockerfile    # RTX 5090 specific layers
├── rtx4090.dockerfile    # RTX 4090 specific layers
└── scripts/
    ├── start.sh          # Main entrypoint
    ├── download_models.py # Model downloader
    └── modules/          # Modular startup scripts
        ├── 01_environment.sh
        ├── 02_update.sh
        ├── 03_ssh.sh
        ├── 04_symlinks.sh
        ├── 05_comfyui.sh
        ├── 06_models.sh   # Checks MODAL_MODELS_PATH for Volume
        └── ...
```

---

## ⚙️ Configuration

### Template Configuration

Templates live in `templates/*/config.yaml`:

```yaml
# templates/boomboom/config.yaml
name: boomboom
version: 1.0.0
description: Flux Kontext template
gpu_requirement: 24GB

comfy_args:
  - --preview-method=auto
  - --use-pytorch-cross-attention

models:
  - source: huggingface
    repo: black-forest-labs/FLUX.1-kontext-dev
    file: flux1-kontext-dev.safetensors
    path: unet

  - source: huggingface
    repo: comfyanonymous/flux_text_encoders
    file: clip_l.safetensors
    path: text_encoders
```

### GPU Mapping

| `gpu_requirement` | Modal GPU |
|-------------------|-----------|
| 12GB | T4 |
| 16GB | L4 |
| 24GB | A10G |
| 40GB | A100 |
| 48GB | L40S |
| 80GB | A100 |

---

## 🔧 Commands

### Download Models

```bash
# Download all models from config.yaml to Volume
modal run platform/modal/download.py --template boomboom

# List models in Volume
modal run platform/modal/download.py --list-only
```

### Serve ComfyUI

```bash
# Development mode (hot reload, no snapshots)
modal serve platform/modal/serve.py

# Production (memory snapshots enabled)
modal deploy platform/modal/serve.py
```

### Volume Management

```bash
# List Volume contents
modal volume ls aiclipse-models

# Delete Volume (start fresh)
modal volume delete aiclipse-models
```

---

## 💾 Volumes

Three persistent Volumes are created automatically:

| Volume | Path | Purpose |
|--------|------|---------|
| `aiclipse-models` | `/modal-volumes/models` | Model weights (~50GB) |
| `aiclipse-outputs` | `/modal-volumes/outputs` | Generated images |
| `aiclipse-workflows` | `/modal-volumes/workflows` | Saved workflows |

### Volume Integration

The `serve.py` entrypoint:
1. Checks for pre-downloaded models in Volume
2. Creates symlinks to `/workspace/aiclipse/models/`
3. Sets `SKIP_MODEL_DOWNLOAD=true` if models exist
4. start.sh respects this and skips downloads

---

## ⚡ Performance

### Download Performance

| Metric | Value |
|--------|-------|
| Connections per file | 16 |
| Parallel files | 4 |
| Throughput | ~180 MB/s |
| 25GB download | ~3 minutes |
| HF optimization | `HF_XET_HIGH_PERFORMANCE=1` |

### Cold Start Performance

| Mode | Cold Start | Notes |
|------|------------|-------|
| `modal serve` | ~60s | No snapshots |
| `modal deploy` | ~30s | Memory snapshot |
| With GPU snapshot | ~5-10s | Experimental |

---

## 🔐 Environment Variables

### Set by serve.py

| Variable | Description |
|----------|-------------|
| `TEMPLATE_TYPE` | Template name (e.g., "boomboom") |
| `TEMPLATE_VERSION` | Template version |
| `COMFY_ARGS` | ComfyUI CLI arguments |
| `MODAL_MODELS_PATH` | Volume models path |
| `MODAL_OUTPUTS_PATH` | Volume outputs path |
| `SKIP_MODEL_DOWNLOAD` | Skip downloads if models exist |
| `DOWNLOAD_MODELS` | Whether to download models |

### Read from Environment

| Variable | Description |
|----------|-------------|
| `AICLIPSE_TEMPLATE` | Override default template |
| `HF_TOKEN` | HuggingFace auth (from secrets) |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 key |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret |
| `R2_BUCKET` | R2 bucket name |
| `R2_ACCOUNT_ID` | R2 account |

---

## 🔑 Secrets

Create Modal secrets for authentication:

```bash
# HuggingFace and common env vars
modal secret create aiclipse-env \
  HF_TOKEN=hf_xxx \
  CIVITAI_API_KEY=xxx

# R2 credentials (optional)
modal secret create r2-credentials \
  R2_ACCESS_KEY_ID=xxx \
  R2_SECRET_ACCESS_KEY=xxx \
  R2_BUCKET=your-bucket \
  R2_ACCOUNT_ID=xxx
```

---

## 🛠️ Development

### Local Testing

```bash
# Check config parsing
python -c "from platform.modal.serve import load_template_config; print(load_template_config('boomboom'))"

# Validate Modal app
modal app list
```

### Adding a New Template

1. Create `templates/new-template/config.yaml`
2. Add GHCR image to `TEMPLATE_IMAGES` in `serve.py`
3. Run `modal run platform/modal/download.py --template new-template`
4. Deploy with custom template:
   ```bash
   AICLIPSE_TEMPLATE=new-template modal deploy platform/modal/serve.py
   ```

### Debugging

```bash
# View container logs
modal app logs aiclipse-comfyui

# Interactive shell
modal shell platform/modal/serve.py
```

---

## 📊 Monitoring

### Dashboard

View live metrics at: `https://modal.com/apps/YOUR_WORKSPACE/main/aiclipse-comfyui`

### Health Check

```python
# In code
ComfyUI().health.remote()  # Returns {"status": "healthy", "comfyui": "running"}
```

---

## 🔄 RunPod Parity

This Modal deployment maintains parity with RunPod:

| Feature | RunPod | Modal |
|---------|--------|-------|
| Config source | `templates/*/config.yaml` | Same |
| Docker image | GHCR | Same |
| Start script | `/scripts/start.sh` | Same |
| Model paths | `/workspace/aiclipse/models` | Symlinked from Volume |
| GPU selection | Pod config | `gpu_requirement` mapping |

---

## 📝 License

Part of the AiClipse ComfyUI project.
