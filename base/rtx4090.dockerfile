ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-common:latest
FROM ${BASE_IMAGE}

ENV GPU_TYPE="rtx4090"
ENV CUDA_VERSION="12.4"
ENV TORCH_INDEX="https://download.pytorch.org/whl/cu124"
ENV TORCH_VERSION="2.6.0+cu124"
ENV XFORMERS_VERSION="0.0.29.post3"

# Install PyTorch and GPU-specific packages
RUN /venv/bin/pip install --no-cache-dir \
    torch=="${TORCH_VERSION}" torchvision torchaudio --index-url ${TORCH_INDEX} && \
    /venv/bin/pip install --no-cache-dir \
    xformers=="${XFORMERS_VERSION}" --index-url ${TORCH_INDEX}

# Copy all setup scripts
COPY base/scripts/ /scripts/
RUN chmod +x /scripts/*.sh /scripts/*.py

# Health check - improved version
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || curl -f http://localhost:8188/ || exit 1

EXPOSE 22 8188 8080 8888 8048
CMD ["/scripts/start.sh"]
