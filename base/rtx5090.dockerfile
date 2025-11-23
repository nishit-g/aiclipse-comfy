ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-common:latest
FROM ${BASE_IMAGE}

ENV GPU_TYPE="rtx5090"
ENV CUDA_VERSION="12.8.0"
ENV TORCH_INDEX="https://download.pytorch.org/whl/cu128"
ENV TORCH_VERSION="2.8.0+cu128"
ENV XFORMERS_VERSION="0.0.32.post1"
ENV ENABLE_SAGE_ATTENTION=true
ENV TORCH_CUDA_ARCH_LIST="10.0+PTX"

# Upgrade to CUDA 12.8.0 for RTX 5090
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cuda-minimal-build-12-8 \
    cuda-cusparse-dev-12-8 \
    cuda-cublas-dev-12-8 \
    && rm -rf /var/lib/apt/lists/*

# Set CUDA 12.8 paths
ENV PATH=/usr/local/cuda-12.8/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:${LD_LIBRARY_PATH}

# Install PyTorch, SageAttention and GPU-specific packages
RUN /venv/bin/pip install --no-cache-dir \
    torch=="${TORCH_VERSION}" torchvision torchaudio --index-url ${TORCH_INDEX}

RUN /venv/bin/pip install --no-cache-dir \
    xformers=="${XFORMERS_VERSION}" --index-url ${TORCH_INDEX}

RUN /venv/bin/pip install --no-cache-dir --no-build-isolation \
    triton ninja sageattention

# Copy all setup scripts
COPY base/scripts/ /scripts/
RUN chmod +x /scripts/*.sh /scripts/*.py

# Health check - improved version
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || curl -f http://localhost:8188/ || exit 1

EXPOSE 22 8188 8080 8888 8048
CMD ["/scripts/start.sh"]
