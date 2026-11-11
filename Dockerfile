# OpenRU-X6 simulation image.
# Base image already contains Python 3.12, PyTorch 2.9.1+cu128 and Sionna 2.2.0.
# Pinned by local registry tag; the build records its digest in results/.
ARG BASE_IMAGE=sionna:2.2.0
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    OPENRU_CONFIG_DIR=/workspace/configs

# Base image already provides UID/GID 1000 (ubuntu), matching the host user.
WORKDIR /workspace

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock

# Docker CLI is used only by E10 to launch the pinned OCUDU image.  The compose
# file mounts the host Docker socket for this lab; see README security notes.
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io \
 && rm -rf /var/lib/apt/lists/*
USER ubuntu

COPY pyproject.toml README.md ./
COPY openru_x6 ./openru_x6
COPY configs ./configs
COPY tests ./tests
COPY scripts ./scripts
COPY reports ./reports
COPY docs ./docs
COPY Makefile ./

USER root
RUN mkdir -p /tmp/openru-build \
 && cp -a pyproject.toml README.md openru_x6 /tmp/openru-build/ \
 && python -m pip install --no-deps /tmp/openru-build \
 && rm -rf /tmp/openru-build \
 && mkdir -p /workspace/results

USER ubuntu

CMD ["python", "-m", "openru_x6.cli", "--help"]
