ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx5090:latest
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

ENV MODELS_MANIFEST="/manifests/boomboom_models.txt"
ENV NODES_MANIFEST="/manifests/boomboom_nodes.txt"

CMD ["/scripts/start.sh"]
