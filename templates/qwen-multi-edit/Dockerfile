# ==============================================================================
# Qwen-Image-Edit-2511 Template
# Ultra-fast image editing with Lightning acceleration
# ==============================================================================
ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-comfyui:rtx5090-latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="qwen-multi-edit"

# Copy template configuration and workflows
COPY config.yaml /templates/qwen-multi-edit/config.yaml
COPY workflows/ /templates/qwen-multi-edit/workflows/

CMD ["/scripts/start.sh"]
