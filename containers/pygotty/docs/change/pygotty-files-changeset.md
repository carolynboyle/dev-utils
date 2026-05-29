# pygotty_files — Changeset

**Location:** `dev-utils/containers/pygotty/pygotty_files/`  
**Purpose:** GoTTY serving bash with a host directory volume-mounted read-only.  
**Parent:** `containers/pygotty/`  
**Port:** 8092 (8090 = python3, 8091 = bash, 8092 = pygotty_files)

All four files are new. No existing files are modified.

---

## File 1: `Dockerfile`

**Path:** `containers/pygotty/pygotty_files/Dockerfile`

**BEFORE:** (new file)

**AFTER:**
```dockerfile
# containers/pygotty/pygotty_files/Dockerfile
#
# Python slim base with GoTTY binary.
# Serves bash with a host directory volume-mounted read-only.
# Mount path configured via PYGOTTY_FILES_HOST_PATH in .env.
# Identical build to pygotty/bash — difference is in docker-compose.yml.

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

CMD ["gotty", "--permit-write", "--port", "8080", "bash"]
```

**Why:** Build is identical to pygotty/bash. The volume mount is
declared in docker-compose.yml, not the Dockerfile — keeps the
image reusable regardless of what path gets mounted.

---

## File 2: `docker-compose.yml`

**Path:** `containers/pygotty/pygotty_files/docker-compose.yml`

**BEFORE:** (new file)

**AFTER:**
```yaml
# containers/pygotty/pygotty_files/docker-compose.yml
#
# pygotty_files — bash shell with read-only host filesystem mount.
# Access: http://localhost:${PYGOTTY_FILES_PORT:-8092}
#
# Usage:
#   cp .env.example .env
#   edit .env — set PYGOTTY_FILES_HOST_PATH to the directory to mount
#   docker-compose up -d
#   open http://localhost:8092
#
# The mounted directory appears at /files inside the container.
# Read-only — the container can never write to your host filesystem.

services:

  pygotty-files:
    build: .
    container_name: pygotty_files
    restart: unless-stopped
    ports:
      - "127.0.0.1:${PYGOTTY_FILES_PORT:-8092}:8080"
    volumes:
      - ${PYGOTTY_FILES_HOST_PATH}:/files:ro
```

**Why:** Volume mount is `:ro` (read-only) — the container can walk
and read the mounted directory but cannot write to it. Mount point
is `/files` inside the container — predictable, obvious, easy to
navigate to with `cd /files`. Host path comes from `.env` so no
paths are hardcoded.

---

## File 3: `.env.example`

**Path:** `containers/pygotty/pygotty_files/.env.example`

**BEFORE:** (new file)

**AFTER:**
```bash
# containers/pygotty/pygotty_files/.env.example
# Copy to .env and adjust as needed.
# .env is gitignored — never commit it.
# Port pygotty_files listens on (host side)
PYGOTTY_FILES_PORT=8092

# Host directory to mount read-only inside the container at /files
# Examples:
#   PYGOTTY_FILES_HOST_PATH=/home/carolyn/projects
#   PYGOTTY_FILES_HOST_PATH=/home/carolyn/projects/dev-utils
#   PYGOTTY_FILES_HOST_PATH=/home/carolyn/projects/dr-filewalker
PYGOTTY_FILES_HOST_PATH=/home/carolyn/projects
```

**Why:** Examples show the range of valid paths — full projects
directory or a single repo. Change per use case without touching
docker-compose.yml.

---

## File 4: `README.md`

**Path:** `containers/pygotty/pygotty_files/README.md`

**BEFORE:** (new file)

**AFTER:**
```markdown
# pygotty_files

GoTTY serving a bash shell with a host directory mounted read-only
inside the container at `/files`.

The container can walk, read, and inspect the mounted directory
but cannot write to it. Your host filesystem is never modified.

Part of the pygotty container family in dev-utils.

---

## Quick Start

```bash
cp .env.example .env
# Edit .env — set PYGOTTY_FILES_HOST_PATH to the directory you want to browse
docker-compose up -d
open http://localhost:8092
```

Inside the browser tab:
```bash
cd /files
ls
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PYGOTTY_FILES_PORT` | `8092` | Host port |
| `PYGOTTY_FILES_HOST_PATH` | `/home/carolyn/projects` | Directory to mount |

---

## All pygotty containers

| Container | Port | Serves |
|---|---|---|
| pygotty | 8090 | python3 REPL |
| pygotty/bash | 8091 | bash shell |
| pygotty/pygotty_files | 8092 | bash + read-only host mount |

All three can run simultaneously.

---

## Stop

```bash
docker-compose down
```

---

## Security Hardening

See `../roadmap.md` — same hardening sequence applies.
Basic auth is especially important here since this container
has visibility into your host filesystem.

---

## Part of Project Crew

- **pygotty** (parent) — python3 REPL proof-of-concept
- **dr-filewalker** — the tool this container previews
- **dev-utils** — home for all Project Crew containers
```

---

## How to run it

```bash
cd dev-utils/containers/pygotty/pygotty_files
cp .env.example .env
# set PYGOTTY_FILES_HOST_PATH in .env
docker-compose up -d
open http://localhost:8092
```

## What to check

- [ ] Browser tab opens, bash prompt appears
- [ ] `cd /files && ls` shows your host directory contents
- [ ] Cannot write to `/files` (try `touch /files/test` — should fail with permission denied)
- [ ] All three pygotty containers running simultaneously (`docker compose ps` from each directory)
