# Dockerfile

**Path:** containers/python-test/Dockerfile
**Syntax:** text
**Generated:** 2026-05-11 15:11:09

```
# =============================================================================
# python-test
# Generic Python 3.11 test container
# =============================================================================
#
# Clean slate for testing Python tools and scripts.
# Non-root user, curl and git included, nothing else pre-installed.
#
# Build:
#   docker compose up --build
#
# =============================================================================

FROM python:3.11-slim

# Prevent .pyc files, force stdout/stderr unbuffered, disable pip noise
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash devuser

# Working directory, owned by devuser
RUN mkdir -p /app && chown devuser:devuser /app
WORKDIR /app

# Switch to non-root user
USER devuser

CMD ["/bin/bash"]

```
