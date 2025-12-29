ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Install ComfyUI v0.6.0 via Git
# We clone directly to the target directory
RUN --mount=type=cache,target=/root/.cache/uv \
    git clone --depth 1 --branch v0.6.0 https://github.com/comfyanonymous/ComfyUI.git /workspace/aiclipse/ComfyUI && \
    cd /workspace/aiclipse/ComfyUI && \
    /venv/bin/uv pip install --no-cache-dir -r requirements.txt

# Install ComfyUI Manager
RUN --mount=type=cache,target=/root/.cache/uv \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git /workspace/aiclipse/ComfyUI/custom_nodes/ComfyUI-Manager && \
    cd /workspace/aiclipse/ComfyUI/custom_nodes/ComfyUI-Manager && \
    /venv/bin/uv pip install --no-cache-dir -r requirements.txt

# Configure ComfyUI Manager (Offline Mode)
# We create the config file so it doesn't try to phone home/update on startup
RUN mkdir -p /workspace/aiclipse/ComfyUI/user && \
    echo '{"network_mode": "offline"}' > /workspace/aiclipse/ComfyUI/user/manager_config.json

# Note: Model directories are created at runtime by 06_models.sh
# This allows for flexibility without rebuilding the image

# Clean up any build artifacts
RUN rm -rf /root/.cache/pip
