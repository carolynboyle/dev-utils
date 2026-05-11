# README.md

**Path:** containers/python-test/README.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# python-test

Generic Python 3.11 test container. Clean slate for testing Python tools and
scripts. Non-root user, curl and git included, nothing else pre-installed.

This image is also used as the base for `dev-utils-test`.

---

## Quick Start

```bash
cp .env.example .env
# Edit .env and fill in your values
docker compose up --build
docker compose exec python-test bash
```

---

## What This Does To Your Computer

- Pulls `python:3.11-slim` from Docker Hub on first build
- Creates a local Docker image tagged `python-test`
- Mounts `HOST_WORKDIR` from your host into `/app` inside the container
- Creates an isolated bridge network (`python_test_net`) — internet access
  via NAT, no access to your LAN

Nothing is written outside of Docker's own storage and your configured
`HOST_WORKDIR`.

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|---|---|
| `DEVUSER_UID` | Your host UID (`id -u`) |
| `DEVUSER_GID` | Your host GID (`id -g`) |
| `HOST_WORKDIR` | Absolute path to mount as `/app` in the container |
| `LAN_SUBNET` | Your LAN subnet — reference only, not used by Docker in host mode |
| `LAN_GATEWAY` | Your LAN gateway — reference only, not used by Docker in host mode |

---

## Network Modes

| File | Access |
|---|---|
| `docker-compose.yml` | Isolated — internet via NAT, no LAN |
| `docker-compose.lan.yml` | Full host network — LAN, steward, ansible targets |

```bash
# Isolated (default)
docker compose up --build

# LAN access
docker compose -f docker-compose.lan.yml up --build
```

---

## Useful Commands

```bash
# Build and start
docker compose up --build

# Open a shell in the running container
docker compose exec python-test bash

# Stop and remove the container
docker compose down

# Remove the image and start fresh
docker compose down --rmi local
```

---

## Part of dev-utils

See `containers/dev-utils-test/` for a version of this container with
setupkit pre-installed.

```
