# ollama_gotty

GoTTY + bash + Ollama in a browser tab.

Open a browser tab, get a bash shell with a running Ollama backend.
Pull any model, run it, talk to it — all from the browser.
Accessible over local network and mesh.

Part of the pygotty container family in dev-utils.

---

## Quick Start

```bash
cp .env.example .env
docker-compose up -d
open http://<your-mac-ip>:8093
```

Inside the browser tab:
```bash
ollama pull qwen2.5:9b
ollama run qwen2.5:9b
```

Models persist in a named Docker volume across container restarts.

---

## Port

Default: `http://0.0.0.0:8093` (all interfaces)

Change `OLLAMA_GOTTY_HOST` in `.env` to restrict to a specific interface.

---

## All pygotty containers

| Container | Port | Serves |
|---|---|---|
| pygotty | 8090 | python3 REPL |
| pygotty/bash | 8091 | bash shell |
| pygotty/pygotty_files | 8092 | bash + read-only host mount |
| pygotty/ollama_gotty | 8093 | bash + Ollama |

---

## Stop

```bash
docker-compose down
```

Models are preserved in the named volume. To remove them:
```bash
docker-compose down -v
```

---

## Security Hardening

See `../roadmap.md`. This container is bound to all interfaces
by default — basic auth should be added before any exposure
beyond your trusted local network or mesh.

---

## Part of Project Crew

- **pygotty** (parent) — python3 REPL proof-of-concept
- **dr-filewalker** — the tool this container family will eventually serve
- **dev-utils** — home for all Project Crew containers
```

---

## How to run it

```bash
cd dev-utils/containers/pygotty/ollama_gotty
cp .env.example .env
docker-compose up -d
open http://<your-mac-ip>:8093
```

## What to check

- [ ] Browser tab opens, bash prompt appears
- [ ] `ollama list` shows no models (empty, expected)
- [ ] `ollama pull qwen2.5:9b` downloads successfully
- [ ] `ollama run qwen2.5:9b` starts a chat session
- [ ] Container restarts cleanly with model still present (`docker-compose restart`)
- [ ] Accessible from another device on local network or mesh