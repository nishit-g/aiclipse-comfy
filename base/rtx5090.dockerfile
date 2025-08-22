ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV GPU_TYPE="rtx5090"
ENV CUDA_VERSION="12.8"
ENV TORCH_INDEX="https://download.pytorch.org/whl/cu128"
ENV TORCH_VERSION="2.8.0+cu128"
ENV XFORMERS_VERSION="0.0.32.post1"
ENV ENABLE_SAGE_ATTENTION=true

# Install PyTorch, SageAttention and GPU-specific packages
RUN /venv/bin/pip install --no-cache-dir \
    torch=="${TORCH_VERSION}" torchvision torchaudio --index-url ${TORCH_INDEX} && \
    /venv/bin/pip install --no-cache-dir \
    xformers=="${XFORMERS_VERSION}" --index-url ${TORCH_INDEX} && \
    /venv/bin/pip install --no-cache-dir \
    triton ninja sageattention

# Copy all setup scripts
COPY base/scripts/ /scripts/
RUN chmod +x /scripts/*.sh /scripts/*.py

# Health check - improved version
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || curl -f http://localhost:8188/ || exit 1

EXPOSE 22 8188 8080 8888 8048
CMD ["/scripts/start.sh"]
