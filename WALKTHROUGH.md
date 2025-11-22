# AiClipse ComfyUI Walkthrough

This guide explains how to build, deploy, and use the AiClipse ComfyUI system. It focuses on the `sd15-basic` template as a primary example.

## 1. System Overview

AiClipse ComfyUI is a layered Docker system designed for RunPod:
1.  **Base Images**: Provide the OS, CUDA drivers, Python environment, and ComfyUI core.
2.  **Templates**: Add specific models, custom nodes, and workflows for a use case (e.g., "SD 1.5 Basic").

## 2. Prerequisites

-   **Docker Desktop**: Installed and running.
-   **Docker Buildx**: Enabled (usually included in modern Docker).
-   **RunPod Account**: For deployment.

## 3. Building Images

You can build images locally using the provided scripts.

### Build Everything
To build all base images and templates:
```bash
./scripts/build.sh all
```

### Build Specific Template
To build just the SD 1.5 Basic template for RTX 4090:
```bash
# First ensure base images are built
./scripts/build.sh base-rtx4090

# Then build the template
docker buildx bake sd15-basic-rtx4090
```

## 4. Deploying to RunPod

Once built and pushed to a registry (e.g., GHCR), you can deploy to RunPod.

1.  **Go to RunPod Console**: [https://runpod.io/console/deploy](https://runpod.io/console/deploy)
2.  **Select GPU**: Choose **RTX 4090** (recommended for cost/performance).
3.  **Configure Template**:
    *   **Image Name**: `ghcr.io/nishit-g/aiclipse-sd15-basic:rtx4090-latest` (or your custom registry).
    *   **Container Disk**: 20GB+ (to hold models).
    *   **Volume Mount**: `/workspace` (Persistent storage).
    *   **Ports**:
        *   `8188` (ComfyUI)
        *   `8080` (FileBrowser)
        *   `22` (SSH)
4.  **Environment Variables**:
    *   `PUBLIC_KEY`: Your SSH public key (optional but recommended).
    *   `HF_TOKEN`: HuggingFace token (if downloading private models).

## 5. Using the System

### Accessing ComfyUI
Once the pod is running, click **Connect** -> **HTTP [8188]**. This opens the ComfyUI interface.

### Running a Workflow
1.  **Load Default**: The template comes with pre-loaded workflows in `/opt/workflows` or `/workspace/aiclipse/workflows`.
2.  **Load Custom**: Drag and drop a `.json` workflow file (like `basic_api.json`) into the window.
3.  **Queue Prompt**: Click "Queue Prompt" to generate an image.

### File Management
Access FileBrowser at port `8080` to manage generated images (`output/`) and upload new models (`models/`).

## 6. Creating a Custom Template

To create a new template (e.g., for a specific client workflow):

1.  **Copy Template**:
    ```bash
    cp -r templates/sd15-basic templates/my-new-template
    ```
2.  **Edit Manifests**:
    *   `models_manifest.txt`: Add required Checkpoints, LoRAs, VAEs.
    *   `nodes_manifest.txt`: Add required Custom Nodes.
3.  **Update Dockerfile**: Change `TEMPLATE_TYPE` and `ENV` variables.
4.  **Register**: Add the new target to `docker-bake.hcl`.
5.  **Build**: `./scripts/build.sh my-new-template`

---

**Summary**:
-   **Build**: Use `./scripts/build.sh` to create Docker images.
-   **Deploy**: Run the image on RunPod with port 8188 exposed.
-   **Create**: Use ComfyUI to generate images.
