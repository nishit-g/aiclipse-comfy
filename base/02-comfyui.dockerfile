ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Install ComfyUI v0.6.0 via Git
# We clone directly to the target directory
RUN --mount=type=cache,target=/root/.cache/uv \
    git clone --depth 1 --branch v0.6.0 https://github.com/comfyanonymous/ComfyUI.git /workspace/aiclipse/ComfyUI && \
    cd /workspace/aiclipse/ComfyUI && \
    uv pip install --no-cache-dir -r requirements.txt

# Install ComfyUI Manager via pip (integrated version)
# Activated at runtime via: COMFY_ARGS="--enable-manager"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache-dir comfyui-manager

# Note: Model directories are created at runtime by 06_models.sh
# This allows for flexibility without rebuilding the image

# Clean up any build artifacts
RUN rm -rf /root/.cache/pip
