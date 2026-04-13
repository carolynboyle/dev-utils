# docker-compose.yml

**Path:** containers/adminer/docker-compose.yml
**Syntax:** yaml
**Generated:** 2026-04-13 14:09:28

```yaml
version: '3.8'

services:
  adminer:
    image: adminer:latest
    container_name: adminer
    restart: unless-stopped

    ports:
      - "${ADMINER_TAILSCALE_IP}:8080:8080"
    networks:
      - adminer_net

    read_only: true
    tmpfs:
      - /tmp:mode=1777

    user: "1000:1000"
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges

    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

networks:
  adminer_net:
    driver: bridge
```
