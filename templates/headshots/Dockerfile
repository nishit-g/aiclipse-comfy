ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE=headshots
ENV DOWNLOAD_MODELS=true

COPY download_models.sh /download_models.sh
RUN chmod +x /download_models.sh
