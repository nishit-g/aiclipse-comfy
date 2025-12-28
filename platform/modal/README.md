# AiClipse ComfyUI - Modal Enterprise Deployment

Best-in-class, config-driven Modal deployment for ComfyUI.
**Uses the SAME `config.yaml` files as RunPod** - unified configuration across platforms.

## Architecture

```
templates/boomboom/config.yaml    ← SAME config for RunPod AND Modal
        ↓
┌─────────────────────┐     ┌─────────────────────┐
│  modal/download.py  │     │  modal/serve.py     │
│  (CPU - cheap!)     │     │  (GPU - L40S)       │
│  Reads config.yaml  │     │  Reads config.yaml  │
│  Downloads to       │  →  │  Mounts Volume      │
│  Modal Volume       │     │  Sets env vars      │
└─────────────────────┘     │  start.sh runs      │
                            └─────────────────────┘
```

## Quick Start

```bash
# 1. Install Modal
pip install modal
modal setup

# 2. Pre-download models (CPU - ~$0.10/hr)
modal run platform/modal/download.py --template boomboom

# 3. Deploy (GPU - pay only when used)
modal deploy platform/modal/serve.py
```

## Commands

| Command | Purpose |
|---------|---------|
| `modal run download.py --template X` | Pre-download models to Volume (CPU) |
| `modal run download.py --list-only` | List models in Volume |
| `modal serve serve.py` | Dev mode with hot-reload |
| `modal deploy serve.py` | Production deployment |

## How It Works

### Adding a New Model

Edit `templates/boomboom/config.yaml`:
```yaml
models:
  - source: huggingface
    repo: new-org/new-model
    file: model.safetensors
    path: checkpoints
```

Then:
```bash
modal run download.py --template boomboom  # Downloads to Volume
modal deploy serve.py                       # Deploys with new model
```

### Adding a New Node

Edit `templates/boomboom/config.yaml`:
```yaml
nodes:
  - repo: https://github.com/user/new-node
    branch: main
```

Nodes are installed by `start.sh` at container startup.

### Adding a New Template

1. Create `templates/my-template/config.yaml`
2. Add image to `serve.py` TEMPLATE_IMAGES dict
3. Run `modal run download.py --template my-template`
4. Set `AICLIPSE_TEMPLATE=my-template` and deploy

## Files

| File | Purpose |
|------|---------|
| `serve.py` | GPU server - reads config.yaml, mounts Volumes |
| `download.py` | CPU downloader - pre-populates Volume |
| `config/templates.py` | Config loader (dataclasses) |
| `config/volumes.py` | Volume definitions |
| `config/secrets.py` | Secrets management |

## Environment Variables

| Variable | Set By | Purpose |
|----------|--------|---------|
| `MODAL_MODELS_PATH` | serve.py | Path to Modal Volume models |
| `SKIP_MODEL_DOWNLOAD` | 06_models.sh | Skip downloads if Volume has models |
| `TEMPLATE_TYPE` | serve.py | Current template name |
| `COMFY_ARGS` | serve.py | ComfyUI arguments from config |

## Volume Integration

The script `base/scripts/modules/06_models.sh` has been modified to:

1. Check `$MODAL_MODELS_PATH` for pre-downloaded models
2. Create symlinks from Volume to `/workspace/aiclipse/models`
3. Set `SKIP_MODEL_DOWNLOAD=true` to skip downloads
4. Fall back to normal downloads if Volume is empty

## Cost Comparison

| Activity | RunPod | Modal |
|----------|--------|-------|
| Model download | GPU time | CPU (~$0.10/hr) |
| Idle | Full cost | $0 (scale-to-zero) |
| Cold start | ~1 min | ~30s (Volume) or ~5s (snapshot) |
