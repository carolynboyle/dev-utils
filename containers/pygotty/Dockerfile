# containers/pygotty/Dockerfile
#
# Python slim base with GoTTY binary copied in.
# GoTTY binary sourced from sorenisanerd/gotty (actively maintained fork).
# Runs python3 interactive shell served over WebSocket in a browser tab.

FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && \
    curl -fsSL -o /tmp/gotty.tar.gz \
      https://github.com/sorenisanerd/gotty/releases/download/v1.6.0/gotty_v1.6.0_linux_amd64.tar.gz && \
    tar -xz -f /tmp/gotty.tar.gz -C /usr/local/bin && \
    rm /tmp/gotty.tar.gz && \
    apt-get remove -y curl && apt-get autoclean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash pygotty

USER pygotty
WORKDIR /home/pygotty

CMD ["gotty", "--permit-write", "--port", "8080", "python3"]

