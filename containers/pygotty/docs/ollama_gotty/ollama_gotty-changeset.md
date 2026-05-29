# ollama_gotty — Changeset

**Location:** `dev-utils/containers/pygotty/ollama_gotty/`  
**Purpose:** GoTTY + bash + Ollama in one container. Browser tab access to a  
terminal with a local LLM backend running alongside it.  
**Base:** `pygotty/bash` pattern (same GoTTY binary, same non-root user)  
**Network:** Local network binding (192.168.x.x or mesh) — not localhost-only  
**Models:** Pulled manually after startup — container starts empty  

All six files are new. No existing files are modified.

---

## File 1: `Dockerfile`

**Path:** `containers/pygotty/ollama_gotty/Dockerfile`

**BEFORE:** (new file)

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

# Install curl for downloading binaries
RUN apt-get update && apt-get install -y curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install GoTTY binary
RUN curl -fsSL -o /tmp/gotty.tar.gz \
      https://github.com/sorenisanerd/gotty/releases/download/v1.6.0/gotty_v1.6.0_linux_amd64.tar.gz && \
    tar -xz -f /tmp/gotty.tar.gz -C /usr/local/bin && \
    rm /tmp/gotty.tar.gz

# Install Ollama binary
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Clean up curl (no longer needed)
RUN apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash pygotty

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER pygotty
WORKDIR /home/pygotty

# Ollama model storage (mounted as named volume)
ENV OLLAMA_MODELS=/models

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

**Why:** Ollama's install script handles the binary and sets up the
service correctly for the current architecture (Apple Silicon or amd64).
GoTTY is the same binary as pygotty/bash. The entrypoint script starts
Ollama in the background before handing off to GoTTY — that sequencing
is the key difference from the bash container.

---

## File 2: `entrypoint.sh`

**Path:** `containers/pygotty/ollama_gotty/entrypoint.sh`

**BEFORE:** (new file)

**AFTER:**
```bash
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
```

**Why:** Ollama must be running before the user reaches the bash prompt,
otherwise `ollama run` commands will fail immediately. The 30-second wait
loop is generous but safe — Ollama typically starts in 2-3 seconds.
`exec` replaces the shell with GoTTY so GoTTY becomes PID 1's child and
Docker stop signals are handled cleanly.

---

## File 3: `docker-compose.yml`

**Path:** `containers/pygotty/ollama_gotty/docker-compose.yml`

**BEFORE:** (new file)

**AFTER:**
```yaml
# containers/pygotty/ollama_gotty/docker-compose.yml
#
# ollama_gotty — GoTTY + bash + Ollama in a browser tab.
# Access: http://<host-ip>:${OLLAMA_GOTTY_PORT:-8093}
#
# Usage:
#   cp .env.example .env
#   edit .env — set OLLAMA_GOTTY_HOST to your local or mesh IP
#   docker-compose up -d
#   open http://<host-ip>:8093
#   ollama pull qwen2.5:9b   (inside the browser tab)

services:

  ollama-gotty:
    build: .
    container_name: ollama_gotty
    restart: unless-stopped
    ports:
      - "${OLLAMA_GOTTY_HOST:-0.0.0.0}:${OLLAMA_GOTTY_PORT:-8093}:8080"
    volumes:
      - ollama_models:/models    # persist models across restarts
    environment:
      - OLLAMA_MODELS=/models
      - GOTTY_PORT=8080

volumes:
  ollama_models:
    driver: local
```

**Why:** Bound to `0.0.0.0` by default (all interfaces) so it's
reachable over the local network and mesh without configuration.
Set `OLLAMA_GOTTY_HOST` in `.env` to lock it to a specific interface
(e.g. your Tailscale IP) once you know what you want. Named volume
for models means `ollama pull` results survive container restarts —
you don't re-download multi-GB models every time.

---

## File 4: `.env.example`

**Path:** `containers/pygotty/ollama_gotty/.env.example`

**BEFORE:** (new file)

**AFTER:**
```bash
# containers/pygotty/ollama_gotty/.env.example
# Copy to .env and adjust as needed.
# .env is gitignored — never commit it.

# Host interface to bind to
# 0.0.0.0 = all interfaces (local network + mesh accessible)
# 127.0.0.1 = localhost only
# 100.x.x.x = Tailscale mesh IP only
# 192.168.x.x = local network only
OLLAMA_GOTTY_HOST=0.0.0.0

# Port (host side)
OLLAMA_GOTTY_PORT=8093
```

**Why:** The host binding comment explains the four common options
so future you doesn't have to look it up. Default is open for
local network access which is the goal for this container.

---

## File 5: `.gitignore`

**Path:** `containers/pygotty/ollama_gotty/.gitignore`

**BEFORE:** (new file)

**AFTER:**
```gitignore
# containers/pygotty/ollama_gotty/.gitignore
.env
__pycache__/
*.pyc
.DS_Store
.vscode/
*.log
```

---

## File 6: `README.md`

**Path:** `containers/pygotty/ollama_gotty/README.md`

**BEFORE:** (new file)

**AFTER:**
```markdown
# ollama_gotty

GoTTY + bash + Ollama in a browser tab.

Open a browser tab, get a bash shell with a running Ollama backend.
Pull any model, run it, talk to it — all from the browser.
Accessible over local network and mesh.

Part of the pygotty container family in dev-utils.

---

## Quick Start

```bash
cp .env.example .env
docker-compose up -d
open http://<your-mac-ip>:8093
```

Inside the browser tab:
```bash
ollama pull qwen2.5:9b
ollama run qwen2.5:9b
```

Models persist in a named Docker volume across container restarts.

---

## Port

Default: `http://0.0.0.0:8093` (all interfaces)

Change `OLLAMA_GOTTY_HOST` in `.env` to restrict to a specific interface.

---

## All pygotty containers

| Container | Port | Serves |
|---|---|---|
| pygotty | 8090 | python3 REPL |
| pygotty/bash | 8091 | bash shell |
| pygotty/pygotty_files | 8092 | bash + read-only host mount |
| pygotty/ollama_gotty | 8093 | bash + Ollama |

---

## Stop

```bash
docker-compose down
```

Models are preserved in the named volume. To remove them:
```bash
docker-compose down -v
```

---

## Security Hardening

See `../roadmap.md`. This container is bound to all interfaces
by default — basic auth should be added before any exposure
beyond your trusted local network or mesh.

---

## Part of Project Crew

- **pygotty** (parent) — python3 REPL proof-of-concept
- **dr-filewalker** — the tool this container family will eventually serve
- **dev-utils** — home for all Project Crew containers
```

---

## How to run it

```bash
cd dev-utils/containers/pygotty/ollama_gotty
cp .env.example .env
docker-compose up -d
open http://<your-mac-ip>:8093
```

## What to check

- [ ] Browser tab opens, bash prompt appears
- [ ] `ollama list` shows no models (empty, expected)
- [ ] `ollama pull qwen2.5:9b` downloads successfully
- [ ] `ollama run qwen2.5:9b` starts a chat session
- [ ] Container restarts cleanly with model still present (`docker-compose restart`)
- [ ] Accessible from another device on local network or mesh
