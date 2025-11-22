ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx5090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="qwen-multi-edit"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Copy template-specific manifests
COPY models_manifest.txt /manifests/qwen-multi-edit_models.txt
COPY nodes_manifest.txt /manifests/qwen-multi-edit_nodes.txt

# Copy workflows
COPY workflows/ /opt/workflows/

# Set environment variables to point to manifests
ENV MODELS_MANIFEST="/manifests/qwen-multi-edit_models.txt"
ENV NODES_MANIFEST="/manifests/qwen-multi-edit_nodes.txt"

# Optimization for RTX 5090
ENV COMFY_ARGS="--preview-method auto --use-sage-attention --force-fp16"

CMD ["/scripts/start.sh"]
