# README.md

**Path:** containers/adminer/README.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
### **`containers/adminer/README.md`**
```markdown
# Adminer Docker Container

This folder contains a `docker-compose.yml` file to run [Adminer](https://www.adminer.org/) in a Docker container with security hardening.

## Features
- Lightweight database management.
- Runs as a non-root user.
- Read-only filesystem with `/tmp` as `tmpfs`.
- Resource limits (CPU/memory).
- Network isolation (binds to a specific IP via `.env`).

## Prerequisites
- Docker and Docker Compose installed.
- A database server to connect to.

## Setup
1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env




Edit .env to set your ADMINER_TAILSCALE_IP.
Start the container:



docker compose up -d




Access Adminer at http://<ADMINER_TAILSCALE_IP>:8080.
Configuration

Database connection details are entered in Adminer's UI after access.
Security

Container runs with dropped capabilities and no-new-privileges.
Filesystem is read-only except for /tmp.

```
