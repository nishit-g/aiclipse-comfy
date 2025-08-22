ARG BASE_IMAGE=ghcr.io/yourusername/aiclipse-base-rtx4090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="headshots"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Copy template-specific files
COPY models_manifest.txt /manifests/headshots_models.txt
COPY custom_nodes.txt /manifests/headshots_nodes.txt
COPY workflows/ /opt/workflows/

# Install headshot-specific custom nodes
RUN cd /tmp && \
    wget https://github.com/Gourieff/comfyui-reactor-node/archive/main.zip -O reactor.zip && \
    wget https://github.com/ltdrdata/ComfyUI-Impact-Pack/archive/main.zip -O impact.zip && \
    echo "Custom nodes staged for installation"

# Set default manifest
ENV MODELS_MANIFEST="/manifests/headshots_models.txt"

CMD ["/scripts/start.sh"]
