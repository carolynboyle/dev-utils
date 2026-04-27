# dev-utils-test

Python test container with setupkit pre-installed. Use this container to test
the dev-utils provisioning workflow on a clean Python environment without
affecting your host machine.

Extends `python-test` — build that image first.

---

## Quick Start

```bash
# Build python-test base image first
cd ../python-test
docker compose up --build
cd ../dev-utils-test

# Configure and build
cp .env.example .env
# Edit .env and fill in your values
docker compose up --build
docker compose exec dev-utils-test bash
```

---

## What This Does To Your Computer

- Pulls `python-test:latest` from local Docker images (must be built first)
- Installs setupkit from GitHub into the container image at build time
- Mounts `HOST_WORKDIR` from your host into `/app` inside the container
- Mounts `CONFIG_DIR` from your host into `/home/devuser/.config/dev-utils`
  so setupkit can read your plugin configs
- Creates an isolated bridge network (`dev_utils_test_net`) — internet access
  via NAT, no access to your LAN

Nothing is written outside of Docker's own storage and your configured
mount paths.

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|---|---|
| `DEVUSER_UID` | Your host UID (`id -u`) |
| `DEVUSER_GID` | Your host GID (`id -g`) |
| `HOST_WORKDIR` | Absolute path to mount as `/app` in the container |
| `CONFIG_DIR` | Absolute path to your dev-utils config directory |
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
docker compose exec dev-utils-test bash

# Test setupkit is working
docker compose exec dev-utils-test setupkit --help

# Stop and remove the container
docker compose down

# Remove the image and rebuild from scratch
docker compose down --rmi local
docker compose up --build
```

---

## Rebuilding After setupkit Updates

The setupkit install is baked into the image at build time. To pick up a new
version:

```bash
docker compose down --rmi local
docker compose up --build
```

---

## Part of dev-utils

See `containers/python-test/` for the generic base image this container
extends.
