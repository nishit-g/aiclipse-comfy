ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV GPU_TYPE="rtx5090"
ENV CUDA_VERSION="12.8"
ENV TORCH_INDEX="https://download.pytorch.org/whl/cu128"
ENV TORCH_VERSION="2.8.0+cu128"
ENV XFORMERS_VERSION="0.0.32.post1"
ENV ENABLE_SAGE_ATTENTION=true

# Create virtual environment and install PyTorch + SageAttention
RUN python3.12 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir torch=="${TORCH_VERSION}" torchvision torchaudio --index-url ${TORCH_INDEX} && \
    /venv/bin/pip install --no-cache-dir xformers=="${XFORMERS_VERSION}" --index-url ${TORCH_INDEX} && \
    /venv/bin/pip install --no-cache-dir huggingface-hub safetensors accelerate && \
    /venv/bin/pip install --no-cache-dir triton ninja && \
    /venv/bin/pip install --no-cache-dir sageattention

# Copy all setup scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8188/ || exit 1

EXPOSE 22 8188 8080 8888 8048
CMD ["/scripts/start.sh"]
