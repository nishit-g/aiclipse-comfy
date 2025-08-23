ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx5090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="boomboom"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Flux-Kontext requires significant VRAM and performance optimization
ENV ENABLE_SAGE_ATTENTION=true
ENV COMFY_ARGS="--force-fp16 --bf16-vae"

# ================================
# STATIC CONTENT (Workflows only)
# ================================
COPY workflows/ /opt/workflows/

COPY models_manifest.txt /manifests/boomboom_models.txt
COPY nodes_manifest.txt /manifests/boomboom_nodes.txt

# Performance settings for high-end workflows
ENV CONFIG_VALIDATION=true
ENV CONFIG_RETRY_ATTEMPTS=3
ENV CONFIG_TIMEOUT=60

# Flux-Kontext specific environment variables
ENV FLUX_KONTEXT_MODE=true
ENV ENABLE_TORCH_COMPILE=true
ENV ENABLE_TEA_CACHE=true

ENV MODELS_MANIFEST="/manifests/boomboom_models.txt"
ENV NODES_MANIFEST="/manifests/boomboom_nodes.txt"

CMD ["/scripts/start.sh"]
