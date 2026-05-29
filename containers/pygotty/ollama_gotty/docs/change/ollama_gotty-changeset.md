# ollama_gotty — Updated Dockerfile and docker-compose.yml

**Changes from original changeset:**
1. Added `zstd` to apt-get install (required by Ollama install script)
2. Added `/models` directory creation with correct ownership before user switch
3. Added optional host volume mount with configurable ro/rw mode from `.env`

---

## File 1: `Dockerfile`

**Path:** `containers/pygotty/ollama_gotty/Dockerfile`

**BEFORE:** (original changeset version)

**AFTER:**
```dockerfile
# containers/pygotty/ollama_gotty/Dockerfile
#
# GoTTY + bash + Ollama in one container.
# Built on the same pattern as pygotty/bash.
# GoTTY serves bash in a browser tab.
# Ollama runs as a background service inside the container.
# Models are stored in a named volume — persist across restarts.
# Pull models manually after startup: ollama pull qwen2.5:9b

FROM python:3.12-slim

# Install dependencies
# zstd required by Ollama install script for extraction
RUN apt-get update && apt-get install -y curl ca-certificates zstd && \
    rm -rf /var/lib/apt/lists/*

# Install GoTTY binary
RUN curl -fsSL -o /tmp/gotty.tar.gz \
      https://github.com/sorenisanerd/gotty/releases/download/v1.6.0/gotty_v1.6.0_linux_amd64.tar.gz && \
    tar -xz -f /tmp/gotty.tar.gz -C /usr/local/bin && \
    rm /tmp/gotty.tar.gz

# Install Ollama binary
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Clean up curl and zstd (no longer needed after install)
RUN apt-get purge -y curl zstd && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash pygotty

# Create models directory with correct ownership before switching user
RUN mkdir -p /models && chown pygotty:pygotty /models

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER pygotty
WORKDIR /home/pygotty

# Ollama model storage (mounted as named volume)
ENV OLLAMA_MODELS=/models

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

**Why the changes:**
- `zstd` — Ollama install script requires it for extraction; slim base doesn't include it
- `/models` ownership — named volume mounts as root by default; pygotty user needs write access to pull and store models
- Purge after install — keeps image lean; curl and zstd not needed at runtime

---

## File 2: `docker-compose.yml`

**Path:** `containers/pygotty/ollama_gotty/docker-compose.yml`

**BEFORE:** (original changeset version)

**AFTER:**
```yaml
# containers/pygotty/ollama_gotty/docker-compose.yml
#
# ollama_gotty — GoTTY + bash + Ollama in a browser tab.
# Access: http://<host-ip>:${OLLAMA_GOTTY_PORT:-8093}
#
# Usage:
#   cp .env.example .env
#   edit .env — set OLLAMA_GOTTY_HOST, and optionally OLLAMA_GOTTY_FILES_PATH
#   docker-compose up -d
#   open http://<host-ip>:8093
#   ollama pull qwen2.5:9b   (inside the browser tab)
#
# Optional host volume mount:
#   Set OLLAMA_GOTTY_FILES_PATH in .env to mount a directory at /files
#   Set OLLAMA_GOTTY_FILES_MODE to ro (read-only) or rw (read-write)
#   Leave OLLAMA_GOTTY_FILES_PATH commented out to disable the mount

services:

  ollama-gotty:
    build: .
    container_name: ollama_gotty
    restart: unless-stopped
    ports:
      - "${OLLAMA_GOTTY_HOST:-0.0.0.0}:${OLLAMA_GOTTY_PORT:-8093}:8080"
    volumes:
      - ollama_models:/models
      - ${OLLAMA_GOTTY_FILES_PATH:-/dev/null}:/files:${OLLAMA_GOTTY_FILES_MODE:-ro}
    environment:
      - OLLAMA_MODELS=/models
      - GOTTY_PORT=8080

volumes:
  ollama_models:
    driver: local
```

**Why the changes:**
- Optional files volume — `/dev/null` fallback means the mount is harmless when `OLLAMA_GOTTY_FILES_PATH` is not set
- `OLLAMA_GOTTY_FILES_MODE` — ro/rw configurable from `.env`; defaults to `ro` for safety

---

## Rebuild command

```bash
docker-compose down
docker-compose up -d --build
```
