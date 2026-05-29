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