# pygotty/bash — Changeset

**Location:** `dev-utils/containers/pygotty/bash/`  
**Purpose:** GoTTY serving bash — persistent connection, disconnects only on explicit exit.  
**Parent:** `containers/pygotty/` (python3 proof-of-concept)

All four files are new. No existing files are modified.

---

## File 1: `Dockerfile`

**Path:** `containers/pygotty/bash/Dockerfile`

**BEFORE:** (new file)

**AFTER:**
```dockerfile
# containers/pygotty/bash/Dockerfile
#
# Python slim base with GoTTY binary.
# Serves bash — connection persists until user types exit or Ctrl+D.
# Based on containers/pygotty/Dockerfile — same build pattern.

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

# bash keeps the connection alive until explicit exit or Ctrl+D
CMD ["gotty", "--permit-write", "--port", "8080", "bash"]
```

**Why:** Identical build pattern to the parent pygotty container.
Only difference is `bash` instead of `python3` as the wrapped command.
bash does not exit on Ctrl+C, so the connection stays alive until
the user explicitly types `exit` or sends Ctrl+D.

---

## File 2: `docker-compose.yml`

**Path:** `containers/pygotty/bash/docker-compose.yml`

**BEFORE:** (new file)

**AFTER:**
```yaml
# containers/pygotty/bash/docker-compose.yml
#
# pygotty/bash — bash shell in a browser tab via GoTTY.
# Access: http://localhost:${PYGOTTY_BASH_PORT:-8091}
#
# Usage:
#   cp .env.example .env
#   docker-compose up -d
#   open http://localhost:8091

services:

  pygotty-bash:
    build: .
    container_name: pygotty-bash
    restart: unless-stopped
    ports:
      - "127.0.0.1:${PYGOTTY_BASH_PORT:-8091}:8080"    # localhost only
```

**Why:** Separate port (8091) from the parent pygotty container (8090)
so both can run simultaneously. Same localhost-only binding pattern.

---

## File 3: `.env.example`

**Path:** `containers/pygotty/bash/.env.example`

**BEFORE:** (new file)

**AFTER:**
```bash
# containers/pygotty/bash/.env.example
# Copy to .env and adjust as needed.
# .env is gitignored — never commit it.

# Port pygotty-bash listens on (host side)
PYGOTTY_BASH_PORT=8091
```

---

## File 4: `README.md`

**Path:** `containers/pygotty/bash/README.md`

**BEFORE:** (new file)

**AFTER:**
```markdown
# pygotty/bash

GoTTY serving a bash shell in a browser tab.

Connection persists until you explicitly type `exit` or Ctrl+D.
Unlike the parent pygotty container (python3), bash does not exit
on Ctrl+C — interrupt signals go to the running command, not the shell.

Part of the pygotty container family in dev-utils.

---

## Quick Start

```bash
cp .env.example .env
docker-compose up -d
open http://localhost:8091
```

---

## Port

Default: `http://localhost:8091`

Change by editing `PYGOTTY_BASH_PORT` in `.env`.

Both pygotty containers can run simultaneously:
- `localhost:8090` — python3 REPL
- `localhost:8091` — bash shell

---

## Stop

```bash
docker-compose down
```

---

## Security Hardening

See `../roadmap.md` — same hardening sequence applies.
Basic auth and mesh binding are the immediate next steps
before any non-localhost exposure.

---

## Part of Project Crew

- **pygotty** (parent) — python3 REPL proof-of-concept
- **dr-filewalker** — the tool these containers will eventually serve
- **dev-utils** — home for all Project Crew containers
```

---

## How to run it

```bash
cd dev-utils/containers/pygotty/bash
cp .env.example .env
docker-compose up -d
open http://localhost:8091
```

## What to check

- [ ] Browser tab opens, bash prompt appears
- [ ] Ctrl+C does not close the connection
- [ ] `exit` closes the session cleanly
- [ ] Parent pygotty container still running on 8090 simultaneously
