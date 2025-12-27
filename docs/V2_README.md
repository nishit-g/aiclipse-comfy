# AiClipse ComfyUI V2

> **One config file. Modular scripts. No more rebuilds for model changes.**

---

## Quick Start

### 1. Deploy to RunPod

```bash
# Image is pre-built on GitHub Container Registry
ghcr.io/nishit-g/boomboom-rtx5090:latest
```

### 2. SSH into Pod

```bash
# Password is saved to a file (not in logs)
cat /workspace/aiclipse/.ssh_password
```

### 3. ComfyUI

Access at `http://your-pod-ip:8188`

---

## Adding Things (No Rebuild Needed!)

### Add a Model

Edit `templates/boomboom/config.yaml` on GitHub:

```yaml
models:
  - source: huggingface
    repo: stabilityai/stable-diffusion-xl
    file: sd_xl_base_1.0.safetensors
    path: checkpoints
```

Next pod start → downloads automatically.

### Add a Custom Node

```yaml
nodes:
  - repo: https://github.com/someone/ComfyUI-NewNode
```

Next pod start → installs automatically.

---

## Directory Structure

```
/workspace/aiclipse/           ← Persistent storage
├── ComfyUI/                   ← Installation
├── models/                    ← All models
├── workflows/                 ← Saved workflows
├── output/                    ← Generated images
└── .ssh_password              ← SSH password (secure)
```

---

## Config File

All template config is in `templates/<name>/config.yaml`:

```yaml
name: boomboom
version: 2.0.0
gpu_requirement: 24GB

comfy_args:
  - --highvram

models:
  - source: huggingface
    repo: black-forest-labs/FLUX.1-Kontext-dev
    file: flux1-kontext-dev.safetensors
    path: unet

nodes:
  - repo: https://github.com/ltdrdata/ComfyUI-Manager
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_MODELS` | `true` | Download models at startup |
| `AUTO_UPDATE` | `true` | Auto-update scripts from GitHub |
| `COMFY_ARGS` | (from config) | Override ComfyUI arguments |
| `ENABLE_JUPYTER` | `false` | Start JupyterLab on port 8888 |
| `HF_TOKEN` | - | HuggingFace token for gated models |

---

## Modular Architecture

Scripts are organized as numbered modules:

```
/scripts/
├── start.sh              ← Orchestrator
├── lib/
│   ├── common.sh         ← Constants, utilities
│   ├── yaml.sh           ← Config parsing
│   └── logging.sh        ← Colored logging
└── modules/
    ├── 01_environment.sh
    ├── 02_update.sh
    ├── 03_ssh.sh
    ├── 04_symlinks.sh
    ├── 05_comfyui.sh
    ├── 06_models.sh
    ├── 07_nodes.sh
    ├── 08_workflows.sh
    ├── 09_services.sh
    └── 10_launch.sh
```

---

## What's New in V2

| Feature | V1 | V2 |
|---------|----|----|
| Config format | `.txt` manifests | YAML |
| Scripts | Monolithic | Modular |
| SSH password | Logged | Saved to file |
| Error handling | Partial | `set -euo pipefail` |
| Add models | Edit txt, rebuild | Edit YAML, restart pod |

---

## Troubleshooting

### Models not downloading?

```bash
# Check logs
cat /workspace/aiclipse/logs/models.log

# Force download
DOWNLOAD_MODELS=true /scripts/start.sh
```

### ComfyUI not starting?

```bash
# Check what module failed
journalctl -u comfyui

# Manually start
cd /workspace/aiclipse/ComfyUI
/venv/bin/python main.py --listen 0.0.0.0 --port 8188
```

---

## Support

- Issues: https://github.com/nishit-g/aiclipse-comfy/issues
- Docs: `docs/FINAL_ARCHITECTURE.md`
