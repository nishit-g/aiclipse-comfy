ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx4090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="sd15-basic"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Copy template-specific manifests with consistent naming
COPY models_manifest.txt /manifests/sd15-basic_models.txt
COPY nodes_manifest.txt /manifests/sd15-basic_nodes.txt

# Copy workflows
COPY workflows/ /opt/workflows/

# Set environment variables to point to manifests
ENV MODELS_MANIFEST="/manifests/sd15-basic_models.txt"
ENV NODES_MANIFEST="/manifests/sd15-basic_nodes.txt"

# Basic ComfyUI args for testing
ENV COMFY_ARGS="--preview-method auto"

CMD ["/scripts/start.sh"]
