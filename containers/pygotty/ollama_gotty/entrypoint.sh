#!/bin/bash
# containers/pygotty/ollama_gotty/entrypoint.sh
#
# Starts Ollama as a background service, waits for it to be ready,
# then hands off to GoTTY serving bash.
# GoTTY is the foreground process — when it exits, the container stops.

# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready (max 30 seconds)
echo "Waiting for Ollama to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    sleep 1
done

# Start GoTTY in the foreground
exec gotty --permit-write --port "${GOTTY_PORT:-8080}" bash