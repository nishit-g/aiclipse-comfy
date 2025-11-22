# System Architecture: AiClipse ComfyUI

This document details the architecture of the `aiclipse-comfy` Docker build system. It explains how base images, templates, and runtime scripts interact to create a production-ready ComfyUI environment on RunPod.

## High-Level Overview

The system uses a **multi-stage, layered Docker architecture** to optimize build times and ensure consistency across different GPU types (RTX 4090 vs RTX 5090).

1.  **Base Layer (`base/`)**: Contains the OS, drivers, Python, and ComfyUI core.
2.  **Template Layer (`templates/`)**: Inherits from the Base Layer and adds specific models, nodes, and workflows.
3.  **Runtime Layer (`scripts/`)**: Handles initialization, model downloading, and service startup when the container launches.

---

## Component Breakdown

### 1. Base Images (`base/`)

The foundation of the system. Defined in `base/common.dockerfile` and GPU-specific files.

*   **`base-common`**:
    *   **OS**: Ubuntu 22.04
    *   **Python**: 3.10+
    *   **Tools**: Git, wget, curl, FileBrowser, JupyterLab, SSH.
    *   **ComfyUI**: Clones the ComfyUI repository.
    *   **Manager**: Installs ComfyUI Manager.

*   **`base-rtx4090` / `base-rtx5090`**:
    *   Inherits from `base-common`.
    *   **CUDA**: Installs specific CUDA versions (e.g., 12.1 for 4090, 12.4 for 5090).
    *   **PyTorch**: Installs the matching PyTorch version.
    *   **Optimization**: Sets GPU-specific environment variables (e.g., `TORCH_CUDA_ARCH_LIST`).

### 2. Templates (`templates/`)

Templates define specific use cases. Each template is a directory containing:

*   **`Dockerfile`**: Inherits from a Base Image (ARG `BASE_IMAGE`).
*   **`models_manifest.txt`**: List of models to download (Checkpoint, LoRA, VAE).
*   **`nodes_manifest.txt`**: List of custom nodes to install.
*   **`workflows/`**: JSON workflow files to pre-load.

**Build Process**:
When `docker buildx bake` runs:
1.  It pulls/builds the Base Image.
2.  It copies the manifests and workflows into the image at `/manifests/` and `/opt/workflows/`.
3.  It sets `ENV` variables like `TEMPLATE_TYPE` and `MODELS_MANIFEST`.

### 3. Runtime Scripts (`scripts/` & `base/scripts/`)

These scripts run *inside* the container when it starts on RunPod.

*   **`start.sh`**: The entry point.
    1.  **Init**: Sets up users and permissions.
    2.  **SSH**: Starts the SSH daemon.
    3.  **Services**: Starts FileBrowser and JupyterLab.
    4.  **Models**: Runs `download_models.py` to process `models_manifest.txt`.
    5.  **Nodes**: Runs `install_nodes.py` (or similar logic) to process `nodes_manifest.txt`.
    6.  **ComfyUI**: Starts `main.py` with arguments defined in `COMFY_ARGS`.

*   **`download_models.py`**:
    *   Reads the manifest.
    *   Checks if the model exists in `/workspace/aiclipse/models` (Persistent Volume).
    *   If not, downloads it from HuggingFace or CivitAI.
    *   Uses `aria2c` for fast parallel downloads.

---

## Data Flow: Build to Run

1.  **Developer** runs `./scripts/build.sh sd15-basic`.
2.  **Docker Buildx** builds `base-common` -> `base-rtx4090` -> `sd15-basic-rtx4090`.
3.  **Registry**: Image is pushed to `ghcr.io/...`.
4.  **User** deploys image to RunPod.
5.  **RunPod** mounts `/workspace` volume.
6.  **Container Start**:
    *   `start.sh` executes.
    *   Checks `/workspace/aiclipse/models`.
    *   Downloads missing models defined in the template.
    *   Starts ComfyUI on port 8188.
7.  **User** connects via Browser.

## Key Configuration Files

*   `docker-bake.hcl`: Defines the build graph (targets, inheritance, tags).
*   `scripts/build.sh`: Wrapper script to run Bake commands.
*   `base/scripts/start.sh`: Container entrypoint logic.

## Directory Structure (Runtime)

```
/workspace/
└── aiclipse/
    ├── ComfyUI/         # Symlinked to /opt/ComfyUI or installed here
    ├── models/          # Persistent storage for models
    │   ├── checkpoints/
    │   ├── loras/
    │   └── ...
    ├── output/          # Generated images
    └── workflows/       # User saved workflows
```
