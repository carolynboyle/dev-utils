# pygotty Container — Changeset

**Location:** `dev-utils/containers/pygotty/`  
**Purpose:** Validate GoTTY serving a Python3 interactive shell in a browser tab.  
**Scaffolded with:** `treekit gotty-test.md --output containers` then renamed manually.

All five files are new. No existing files are modified.

---

## File 1: `Dockerfile`

**Path:** `containers/pygotty/Dockerfile`

**BEFORE:** (empty stub)

**AFTER:**
```dockerfile
# containers/pygotty/Dockerfile
#
# Python slim base with GoTTY binary copied in.
# GoTTY binary sourced from sorenisanerd/gotty (actively maintained fork).
# Runs python3 interactive shell served over WebSocket in a browser tab.

FROM python:3.12-slim

# Copy GoTTY binary from the maintained fork image
COPY --from=ghcr.io/sorenisanerd/gotty:latest /usr/local/bin/gotty /usr/local/bin/gotty

# Create a non-root user
RUN useradd --create-home --shell /bin/bash pygotty

USER pygotty
WORKDIR /home/pygotty

# --permit-write  : allow keyboard input (read-only by default)
# --port          : bound to container port, mapped by compose
# python3         : the command GoTTY wraps and serves
CMD ["gotty", "--permit-write", "--port", "8080", "python3"]
```

**Why:** Python slim keeps the image small. GoTTY binary is copied from
the official maintained image rather than downloaded at build time —
reproducible and offline-friendly. Non-root user is the simplest safe
default. `--permit-write` is required for any interactive use; without
it the browser terminal is read-only.

---

## File 2: `docker-compose.yml`

**Path:** `containers/pygotty/docker-compose.yml`

**BEFORE:** (empty stub)

**AFTER:**
```yaml
# containers/pygotty/docker-compose.yml
#
# pygotty — Python3 shell in a browser tab via GoTTY.
# Access: http://localhost:8080
#
# Usage:
#   cp .env.example .env
#   docker-compose up -d
#   open http://localhost:8080

services:

  pygotty:
    build: .
    container_name: pygotty
    restart: unless-stopped
    ports:
      - "127.0.0.1:${PYGOTTY_PORT:-8080}:8080"    # localhost only
```

**Why:** Matches existing container conventions — `127.0.0.1` binding,
`unless-stopped`, port from `.env` with a sane default. Deliberately
minimal: no volumes, no healthcheck, no dependencies. This is a
proof-of-concept container.

---

## File 3: `.env.example`

**Path:** `containers/pygotty/.env.example`

**BEFORE:** (empty stub)

**AFTER:**
```bash
# containers/pygotty/.env.example
# Copy to .env and adjust as needed.
# .env is gitignored — never commit it.

# Port pygotty listens on (host side)
PYGOTTY_PORT=8080
```

**Why:** Keeps port configurable without touching `docker-compose.yml`.
Consistent with your other containers' `.env` pattern.

---

## File 4: `.gitignore`

**Path:** `containers/pygotty/.gitignore`

**BEFORE:** (empty stub)

**AFTER:**
```gitignore
# containers/pygotty/.gitignore
.env
```

**Why:** `.env` must never be committed. One line, nothing else needed.

---

## File 5: `README.md`

**Path:** `containers/pygotty/README.md`

**BEFORE:** (empty stub)

**AFTER:**
```markdown
# pygotty

GoTTY proof-of-concept container for the dev-utils toolkit.

Serves a Python 3 interactive shell in a browser tab over WebSocket.
No installation required on the client — just a browser.

Part of the dr-filewalker evaluation: if GoTTY handles Python's
readline loop cleanly, the dr-filewalker interactive menu will work
the same way.

---

## Quick Start

```bash
cp .env.example .env
docker compose up 
open http://localhost:8080
```

You should see a Python 3 REPL in your browser tab.
Type normally. Ctrl+C works. Ctrl+D exits the Python shell
(GoTTY will show a session closed message).

---

## What's in the container

- Base: `python:3.12-slim`
- GoTTY binary from `sorenisanerd/gotty` (actively maintained fork
  of the original `yudai/gotty`)
- Non-root user (`pygotty`)
- GoTTY wraps `python3` with `--permit-write` (allows keyboard input)

---

## Port

Default: `http://localhost:8080`

Change by editing `PYGOTTY_PORT` in `.env`.

---

## Stop

```bash
docker-compose down
```

---

## Security Hardening (next steps, not implemented here)

This container is for local testing only. Before any public exposure:

1. **Basic auth** — add `--credential user:password` to the GoTTY
   CMD in the Dockerfile. Never expose GoTTY without auth.

2. **TLS** — put nginx in front with a cert (Let's Encrypt).
   GoTTY itself does not terminate TLS in production setups.

3. **Replace bare shell with a scoped command** — for dr-filewalker,
   GoTTY will wrap the `dr-filewalker` CLI, not a raw Python shell.
   A scoped command has no shell escape surface.

4. **`--once` flag** — makes GoTTY exit after the first session ends.
   Useful for single-use admin tasks; not appropriate for a persistent
   service.

5. **Network isolation** — in the full dr-filewalker stack, GoTTY
   and postgres will share a private Docker network. GoTTY is the
   only container with a port exposed to the host.

---

## Part of Project Crew

- **dr-filewalker** — the tool this container will eventually serve
- **treekit** — scaffolded the original directory structure
- **dev-utils** — home for all Project Crew containers

---

## Name

pygotty sounds like something that belongs on PyPI.
Merriam-Webster confirms no naming collision (go potty).
```

**Why:** Documents what's running, why it exists, and the security
hardening roadmap while it's fresh. Records the dr-filewalker
connection for the contest writeup. Includes the naming story because
future you will want to know.

---

## How to run it

```bash
cd dev-utils/containers/pygotty
cp .env.example .env
docker-compose up -d
open http://localhost:8080
```

## What to check

- [x] Browser tab opens, Python 3 prompt appears
- [x] Can type and execute Python expressions
- [x] Arrow key history works (readline)
- [x] Ctrl+C sends KeyboardInterrupt (not killing the container)
- [x] Ctrl+D closes the session gracefully
- [ ] Container restarts cleanly after session closes (`docker compose ps`)

The readline arrow key test is the important one — if history
navigation works through GoTTY, dr-filewalker's menu will work too.
