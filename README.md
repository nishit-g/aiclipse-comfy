# AiClipse ComfyUI Template System ; hi

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-production--ready-green.svg)
![Status](https://img.shields.io/badge/status-fast_as_f***-fire.svg)

A high-performance, production-ready ComfyUI container system designed for speed, agility, and scale. Built for RunPod, Railway, and other container platforms.

## 🚀 Key Features

-   **🔥 Hyper-Fast Downloads**: Uses `aria2c` with 16x parallel connections to saturate 10Gbps+ links.
-   **⚡ Instant Runtime Updates**: Pushing scripts to GitHub updates your container *instantly* on restart. No Docker rebuilds required.
-   **🛡️ Lean Architecture**: Minimal footprint. No bloatware. SSH-first workflow.
-   **🔌 Parallel Node Installation**: Installs custom nodes in parallel for blazing fast startup.
-   **📦 Smart Caching**: Docker layers optimized to prevent cache invalidation.
-   **🛠️ Developer Friendly**: `uv` package manager for fast dependency resolution.

---

## 🏗️ Architecture

This project uses a layered Docker architecture to maximize cache hits and minimize build times.

| Image | Description |
|-------|-------------|
| `base-common` | Ubuntu 22.04 + CUDA 12.4 + Python 3.12 + System Deps (Heavy) |
| `base-rtx4090` | `base-common` + PyTorch 2.4 (CUDA 12.4) + xFormers |
| `base-rtx5090` | `base-common` + PyTorch 2.5 (CUDA 12.8) + SageAttention |
| `templates/*` | Lightweight layers containing specific workflows and configs |

### The "Runtime Update" System

Unlike traditional Docker containers, this system does **not** bake scripts or manifests into the image permanently.

1.  **CI/CD**: GitHub Actions is configured to **IGNORE** changes to `base/scripts/` and `manifests/`.
2.  **Startup**: When the container starts, `start.sh` pulls the latest scripts from this repository.
3.  **Result**: You can update logic, add models, or change nodes **without waiting for a build**.

---

## 🛠️ Usage

### 1. Deployment

Deploy using the pre-built images from GitHub Container Registry:

```bash
# RTX 4090 / L40S / A100
ghcr.io/nishit-g/aiclipse-base-rtx4090:latest

# RTX 5090 (Blackwell)
ghcr.io/nishit-g/aiclipse-base-rtx5090:latest
```

### 2. Environment Variables

Configure the container behavior using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_UPDATE` | `true` | Pull latest scripts from git at startup. |
| `DOWNLOAD_MODELS` | `true` | Enable/Disable model downloads. |
| `ENABLE_JUPYTER` | `false` | Enable JupyterLab (Port 8888). |
| `HF_TOKEN` | - | HuggingFace Token (for private models). |
| `CIVITAI_TOKEN` | - | CivitAI Token (for restricted models). |
| `PUBLIC_KEY` | - | SSH Public Key (for passwordless access). |
| `CONFIG_REPO` | `...` | Git repo to pull scripts from. |
| `CONFIG_BRANCH` | `main` | Branch to use for updates. |

### 3. Managing Models (`models_manifest.txt`)

Models are defined in `manifests/base_models.txt` (or template specific). The format is:

```text
# source|identifier|filename|subdir
huggingface | stabilityai/sdxl-turbo | sdxl_turbo.safetensors | checkpoints
civitai | 123456 | realvis_v4.safetensors | checkpoints
url | https://example.com/model.safetensors | model.safetensors | loras
```

To add a model:
1.  Edit the manifest file in GitHub.
2.  Restart your container.
3.  The system will auto-download it using `aria2c`.

### 4. Managing Nodes (`custom_nodes_manifest.txt`)

Nodes are defined in `manifests/base_nodes.txt`. The format is:

```text
# repo_url | branch | category
https://github.com/ltdrdata/ComfyUI-Manager | main | management
https://github.com/cubiq/ComfyUI_essentials | main | utils
```

To add a node:
1.  Edit the manifest file in GitHub.
2.  Restart your container.
3.  The system will auto-install it (and its requirements) in parallel.

---

## 💻 Development

### Local Build

To build the images locally:

```bash
# Build everything
docker buildx bake all

# Build specific target
docker buildx bake base-rtx4090
```

### Directory Structure

```text
.
├── .github/workflows/   # CI/CD Configuration
├── base/
│   ├── common.dockerfile # Base system image
│   ├── rtx4090.dockerfile # GPU specific layers
│   └── scripts/          # Runtime scripts (Auto-updated)
│       ├── start.sh      # Entrypoint
│       ├── setup_*.sh    # Setup modules
│       └── lib/          # Libraries
├── manifests/            # Model and Node definitions
└── templates/            # Workflow templates
```

---

## ⚡ Performance Tuning

This system is tuned for speed out of the box.

-   **Downloads**: Uses `aria2c` with `-x 16 -s 16 -j 10`. This means up to 160 concurrent connections.
-   **Pip**: Uses `uv` (an extremely fast Rust-based pip replacement).
-   **Git**: Uses shallow clones (`--depth 1`) and parallel execution.

## 🔒 Security

-   **SSH**: Secure access via public key (recommended) or random password.
-   **Lean**: No unnecessary web services running by default.
-   **Secrets**: Supports `HF_TOKEN` and `CIVITAI_TOKEN` for authenticated downloads.

---

## 🤝 Contributing

1.  Fork the repo.
2.  Make your changes to `base/scripts/`.
3.  Push to your fork.
4.  Test by setting `CONFIG_REPO=https://github.com/your-user/repo` in your container.
5.  Submit a PR.
