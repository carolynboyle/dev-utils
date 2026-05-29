

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
