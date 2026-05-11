# docker-compose.yml

**Path:** containers/adminer/docker-compose.yml
**Syntax:** yaml
**Generated:** 2026-05-11 15:11:09

```yaml
# =============================================================================
# Adminer - Hardened Compose File
# =============================================================================
#
# Security measures applied:
#   - Read-only root filesystem
#   - /tmp mounted as tmpfs (required for runtime writes)
#   - All Linux capabilities dropped
#   - no-new-privileges prevents privilege escalation
#   - Memory and CPU limits contain blast radius if compromised
#   - Named network isolates container from default bridge
#   - Port bound to configured interface only (Tailscale recommended)
#   - Image unpinned intentionally -- see README Security section
#
# =============================================================================

services:
  adminer:
    image: adminer:latest
    container_name: adminer
    restart: unless-stopped

    # -------------------------------------------------------------------------
    # Network: bind to configured interface only
    # -------------------------------------------------------------------------
    ports:
      - "${ADMINER_BIND_IP}:8080:8080"
    networks:
      - adminer_net

    # -------------------------------------------------------------------------
    # Filesystem hardening
    # -------------------------------------------------------------------------
    read_only: true
    tmpfs:
      - /tmp:mode=1777

    # -------------------------------------------------------------------------
    # Capability and privilege hardening
    # -------------------------------------------------------------------------
    user: "${ADMINER_UID}:${ADMINER_GID}"
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

    # -------------------------------------------------------------------------
    # Resource limits -- contain blast radius, prevent host starvation
    # -------------------------------------------------------------------------
    deploy:
      resources:
        limits:
          memory: 256m
          cpus: "0.5"

# =============================================================================
# Networks
# =============================================================================
networks:
  adminer_net:
    driver: bridge
```
