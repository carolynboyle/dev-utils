# README.md

**Path:** containers/pgadmin/README.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# pgAdmin 4 Docker Container

Runs [pgAdmin 4](https://www.pgadmin.org/) in a hardened Docker container for
PostgreSQL database management. Access is restricted to a configured network
interface — Tailscale is recommended so the container is never exposed to the
LAN or internet.

## Features

- Read-only root filesystem with `/tmp` and `/run` as tmpfs
- All Linux capabilities dropped
- `no-new-privileges` set
- Configurable bind IP — restrict to Tailscale interface
- Memory and CPU limits
- No credentials hardcoded — all secrets in `.env`
- Persistent configuration survives container recreation via named volume

## Prerequisites

- Docker and Docker Compose installed
- A PostgreSQL server to connect to

## Setup

```bash
cp .env.template .env
chmod 600 .env
# Edit .env -- set PGADMIN_BIND_IP, PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD
docker compose up -d
```

Access pgAdmin at `http://<PGADMIN_BIND_IP>:5050`.

PostgreSQL connection details are configured in the pgAdmin UI after login.

## Security

- All capabilities dropped; `no-new-privileges` prevents privilege escalation
- Read-only filesystem prevents persistent writes to the container
- Bind IP restricts which network interface the port is exposed on
- pgAdmin runs as its own internal non-root user (uid 5050)
- Image is not pinned to a specific digest. `latest` is used intentionally
  so that security patches are applied automatically on container recreation.
  This is acceptable because access is restricted to the Tailscale mesh,
  limiting exposure to supply chain risk.

## Updating

```bash
docker compose pull
docker compose up -d
```
```
