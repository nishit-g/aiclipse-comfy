ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx4090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="headshots"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Copy template-specific model manifest
COPY models_manifest.txt /manifests/headshots_models.txt

# Copy workflows
COPY workflows/ /opt/workflows/

# Set environment to point to the existing manifests
# (These files are already in the base image from manifests/ directory)
ENV MODELS_MANIFEST="/manifests/headshots_models.txt"
ENV NODES_MANIFEST="/manifests/headshots_nodes.txt"

CMD ["/scripts/start.sh"]
