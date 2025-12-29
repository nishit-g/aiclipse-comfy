ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-comfyui:rtx5090-latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="boomboom"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# ================================
# STATIC CONTENT (Workflows only)
# ================================
COPY workflows/ /opt/workflows/

COPY models_manifest.txt /manifests/boomboom_models.txt
COPY nodes_manifest.txt /manifests/boomboom_nodes.txt

ENV MODELS_MANIFEST="/manifests/boomboom_models.txt" \
    NODES_MANIFEST="/manifests/boomboom_nodes.txt" \
    COMFY_DIR="/workspace/aiclipse/ComfyUI"

# Install custom nodes at build time
RUN --mount=type=cache,target=/root/.cache/uv \
    python3 /scripts/build_nodes.py

CMD ["/scripts/start.sh"]
