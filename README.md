# AiClipse ComfyUI V3

🚀 **Production-ready ComfyUI deployment for Modal and RunPod**

[![Modal](https://img.shields.io/badge/Modal-Ready-blue)](https://modal.com)
[![RunPod](https://img.shields.io/badge/RunPod-Ready-purple)](https://runpod.io)

## Features

- ⚡ **Cold Start < 30s** - comfy-cli + v2 Volumes
- 🚀 **aria2c Downloads** - 16 parallel connections, 400+ Mbps
- 🔧 **Config-Driven** - Single `config.yaml` per template
- 📦 **GPU Variants** - RTX 4090/5090, A10G, A100, H100

---

## Quick Start

### Modal (Recommended)

```bash
# 1. Download models (one-time)
modal run v3/templates/qwen-multi-edit/modal/app.py::download_models

# 2. Serve
modal serve v3/templates/qwen-multi-edit/modal/app.py

# 3. Deploy (production)
modal deploy v3/templates/qwen-multi-edit/modal/app.py
```

### RunPod

```bash
# Build image
docker build -f v3/templates/qwen-multi-edit/runpod/Dockerfile -t comfy-qwen:latest .

# Push and deploy to RunPod
```

---

## Project Structure

```
v3/
├── shared/aiclipse/           # Core library
│   ├── config.py              # YAML + env config
│   ├── models.py              # aria2c downloader
│   ├── gpu.py                 # GPU variants
│   ├── comfy.py               # ComfyUI launcher
│   └── paths.py               # Model path setup
└── templates/
    └── qwen-multi-edit/       # Qwen Image Edit template
        ├── config.yaml        # Models, nodes, args
        ├── modal/app.py       # Modal deployment
        ├── runpod/            # RunPod Dockerfile + entrypoint
        └── workflows/         # ComfyUI workflow JSONs
```

---

## Configuration

Edit `v3/templates/qwen-multi-edit/config.yaml`:

```yaml
name: qwen-multi-edit
comfy_args:
  - --highvram
  - --fast fp8_matrix_mult

models:
  - source: huggingface
    repo: Comfy-Org/Qwen-Image-Edit_ComfyUI
    file: split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors
    path: diffusion_models
```

### Environment Overrides

```bash
# Override comfy args
export COMFY_ARGS="--lowvram --preview-method auto"

# Skip model downloads
export SKIP_MODEL_DOWNLOAD=true

# HuggingFace token (for private models)
export HF_TOKEN=hf_xxxxx
```

---

## GPU Support

| GPU | VRAM | Modal | RunPod |
|-----|------|-------|--------|
| A10G | 24GB | ✅ `GPU_VARIANT=a10g` | ✅ |
| RTX 4090 | 24GB | - | ✅ `GPU_VARIANT=rtx4090` |
| RTX 5090 | 32GB | - | ✅ `GPU_VARIANT=rtx5090` |
| A100 | 80GB | ✅ `GPU_VARIANT=a100` | ✅ |
| H100 | 80GB | ✅ `GPU_VARIANT=h100` | ✅ |

---

## License

MIT
