# AiClipse ComfyUI V3 - Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AiClipse ComfyUI V3                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │   config.yaml    │    │    aiclipse/     │    │   Platform       │     │
│   │   (Template)     │───▶│   (Core Lib)     │───▶│   Deployment     │     │
│   └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│                                                                             │
│   Models, Nodes,          Config, Models,          Modal or RunPod         │
│   ComfyUI Args            GPU, Paths               app.py / Dockerfile     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
v3/
├── shared/aiclipse/           # Core Library
│   ├── __init__.py            # Public API exports
│   ├── config.py              # YAML + env config loading
│   ├── models.py              # Model downloader (aria2c, HF, R2)
│   ├── gpu.py                 # GPU variant configs
│   ├── comfy.py               # ComfyUI launcher
│   └── paths.py               # extra_model_paths.yaml setup
│
└── templates/
    └── qwen-multi-edit/       # Template
        ├── config.yaml        # Template configuration
        ├── modal/app.py       # Modal deployment
        ├── runpod/
        │   ├── Dockerfile
        │   └── entrypoint.py
        └── workflows/         # ComfyUI workflow JSONs
```

---

## Core Library (`aiclipse/`)

### `config.py` - Configuration Loading
```python
Config.load("config.yaml")  # Loads YAML with env overrides
```

**Environment Overrides:**
- `COMFY_ARGS` - Override ComfyUI arguments
- `SKIP_MODEL_DOWNLOAD` - Skip model downloads
- `HF_TOKEN` - HuggingFace token
- `R2_*` - Cloudflare R2 credentials

### `models.py` - Model Downloader

**Supports:**
- **HuggingFace** - aria2c parallel downloads (16 connections × 4 files)
- **Cloudflare R2** - boto3 parallel downloads
- **CivitAI** - (Not yet implemented)

**Speed:** 400+ Mbps on Modal infrastructure

### `gpu.py` - GPU Configurations

| Variant | CUDA | VRAM | Modal GPU |
|---------|------|------|-----------|
| RTX 4090 | 12.4 | 24GB | - |
| RTX 5090 | 12.8 | 32GB | - |
| A10G | 12.4 | 24GB | ✅ |
| A100 | 12.4 | 80GB | ✅ |
| H100 | 12.4 | 80GB | ✅ |

### `comfy.py` - ComfyUI Launcher

- Custom node installation (parallel, with retry)
- ComfyUI process management
- comfy-cli integration

### `paths.py` - Model Path Setup

Creates `extra_model_paths.yaml` to configure ComfyUI model locations.

---

## Modal Deployment

### Image Layers

```
┌─────────────────────────────────────────────┐
│  template_image                             │  ← Config, workflows (LIGHT)
├─────────────────────────────────────────────┤
│  comfy_image                                │  ← ComfyUI via comfy-cli (CACHED)
├─────────────────────────────────────────────┤
│  download_image                             │  ← aria2c + aiclipse (for downloads)
├─────────────────────────────────────────────┤
│  base_image                                 │  ← Python + system deps (CACHED LONG)
└─────────────────────────────────────────────┘
```

### Volumes (V2)

| Volume | Mount | Purpose |
|--------|-------|---------|
| `aiclipse-models-v2` | `/models` | Model storage |
| `aiclipse-outputs-v2` | `/outputs` | Generated outputs |

### Functions

| Function | Purpose |
|----------|---------|
| `download_models` | Download all models to volume |
| `serve` | Run ComfyUI web server |
| `health` | Health check endpoint |

---

## Data Flow

### Model Download
```
config.yaml → ModelDownloader → aria2c/boto3 → Modal Volume
```

### Serving
```
Modal Request → serve() → setup_model_paths() → ComfyUI → Response
```

---

## Model Sources

### HuggingFace
```yaml
- source: huggingface
  repo: Comfy-Org/Qwen-Image-Edit_ComfyUI
  file: split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors
  path: diffusion_models
```

### Cloudflare R2
```yaml
- source: r2
  key: loras_v2/v2_hk_000014000.safetensors
  file: v2_hk_000014000.safetensors
  path: loras
```

**Required Environment:**
```bash
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET=models
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
```

---

## Performance

| Metric | Value |
|--------|-------|
| **Cold Start** | ~60-90s (without snapshots) |
| **Download Speed** | 400+ Mbps |
| **GPU** | A10G (24GB VRAM) |
| **Containers** | max_containers=1 |
| **Scaledown** | 5 minutes |

---

## Quick Reference

```bash
# Download models
modal run v3/templates/qwen-multi-edit/modal/app.py::download_models

# Serve (dev)
modal serve v3/templates/qwen-multi-edit/modal/app.py

# Deploy (prod)
modal deploy v3/templates/qwen-multi-edit/modal/app.py
```
