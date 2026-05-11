# SETUP.md

**Path:** containers/setup-tests/SETUP.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# dev-utils Container Setup

Manual setup guide for the dev-utils test containers. Covers the same steps
the `setup.sh` script performs, in the same order, for anyone who prefers to
know exactly what is happening on their machine before it happens.

> **Windows users:** `setup.sh` requires bash and is not supported natively
> on Windows. A PowerShell equivalent (`setup.ps1`) is planned. Until then,
> follow the manual steps in this document using PowerShell or Command Prompt
> where Docker commands are the same, and adjust paths accordingly.

---

## Containers

| Name | Description |
|---|---|
| `python-test` | Generic Python 3.11 environment — clean slate, nothing pre-installed |
| `dev-utils-test` | Python 3.11 with dev-utils setupkit pre-installed |

`dev-utils-test` extends `python-test` — build `python-test` first.

---

## Prerequisites

The following must be installed before setting up either container:

| Tool | Purpose | Install |
|---|---|---|
| Docker Engine | Runs the containers | https://docs.docker.com/engine/install/ |
| Docker Compose v2 | Orchestrates the build | Included with Docker Desktop; `docker compose` plugin for Linux |
| python3 | Used by `setup.sh` to parse `containers.yaml` | https://python.org |
| PyYAML | Python yaml library used by `setup.sh` | See below |
| curl | Fetches files from GitHub | Usually pre-installed on Linux/Mac |

### Installing PyYAML

**Debian / Ubuntu Linux:**
```bash
sudo apt install python3-yaml
```

**Mac (Homebrew Python):**
```bash
pip3 install pyyaml
```

**Other Linux distributions:** Check your distro's package manager for
`python3-yaml` or the equivalent. Most mainstream distributions package it.

> **Windows users:** The planned `setup.ps1` PowerShell script uses the
> `powershell-yaml` module instead and does not require PyYAML at all:
> ```powershell
> Install-Module powershell-yaml
> ```

Verify everything is in place:
```bash
docker --version
docker compose version
python3 --version
python3 -c "import yaml; print('PyYAML ok')"
curl --version
```

---

## Step 1 — Create a working directory

The containers live under `~/containers/`. Create a directory for each one:

```bash
mkdir -p ~/containers/python-test
mkdir -p ~/containers/dev-utils-test    # if setting up dev-utils-test
```

---

## Step 2 — Create the .env file

Each container reads configuration from a `.env` file in its working
directory. This file is never committed to the repo — it contains
environment-specific values that vary per machine.

### Finding your values

**DEVUSER_UID** — your host user ID:
```bash
id -u
```

**DEVUSER_GID** — your host group ID:
```bash
id -g
```

**LAN_SUBNET** — your local network subnet:
```bash
ip route | awk '/proto kernel/ {print $1}' | head -1
```

**LAN_GATEWAY** — your local network gateway:
```bash
ip route | awk '/default/ {print $3}' | head -1
```

**HOST_WORKDIR** — an absolute path on your host to mount as `/app` inside
the container. This is where you'll put files you want to work with inside
the container. Example: `/home/yourname/projects/test-workspace`

**CONFIG_DIR** *(dev-utils-test only)* — absolute path to your dev-utils
config directory. If you haven't set up dev-utils yet, create an empty
directory here and point to it:
```bash
mkdir -p ~/.config/dev-utils
```
Then use `~/.config/dev-utils` as the value (expanded to full path).

### Writing the file

**python-test** — create `~/containers/python-test/.env`:
```bash
DEVUSER_UID=1000
DEVUSER_GID=1000
LAN_SUBNET=192.168.1.0/24
LAN_GATEWAY=192.168.1.1
HOST_WORKDIR=/home/yourname/projects/test-workspace
```

**dev-utils-test** — create `~/containers/dev-utils-test/.env`:
```bash
DEVUSER_UID=1000
DEVUSER_GID=1000
LAN_SUBNET=192.168.1.0/24
LAN_GATEWAY=192.168.1.1
HOST_WORKDIR=/home/yourname/projects/test-workspace
CONFIG_DIR=/home/yourname/.config/dev-utils
```

Replace the example values with the actual values from the commands above.

> **Why these values?**
>
> `DEVUSER_UID` and `DEVUSER_GID` ensure files created inside the container
> are owned by your host user, not root. Without this, files written to
> mounted volumes come back owned by root and require sudo to manage.
>
> `LAN_SUBNET` and `LAN_GATEWAY` are reference values used only when running
> the LAN network variant (`docker-compose.lan.yml`). They are not used by
> the default isolated network mode.
>
> `HOST_WORKDIR` is mounted as `/app` inside the container — it is the
> bridge between your host filesystem and the container.
>
> `CONFIG_DIR` (dev-utils-test only) is mounted as
> `/home/devuser/.config/dev-utils` — it lets setupkit inside the container
> read your plugin configuration from the host without baking it into the
> image.

---

## Step 3 — Fetch container files

Fetch the container definition files from GitHub into your working directory.

### python-test

```bash
cd ~/containers/python-test

BASE="https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/python-test"

curl -fsSL "${BASE}/Dockerfile"             -o Dockerfile
curl -fsSL "${BASE}/docker-compose.yml"     -o docker-compose.yml
curl -fsSL "${BASE}/docker-compose.lan.yml" -o docker-compose.lan.yml
curl -fsSL "${BASE}/README.md"              -o README.md
```

### dev-utils-test

```bash
cd ~/containers/dev-utils-test

BASE="https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/dev-utils-test"

curl -fsSL "${BASE}/Dockerfile"             -o Dockerfile
curl -fsSL "${BASE}/docker-compose.yml"     -o docker-compose.yml
curl -fsSL "${BASE}/docker-compose.lan.yml" -o docker-compose.lan.yml
curl -fsSL "${BASE}/README.md"              -o README.md
```

---

## Step 4 — Build python-test first (dev-utils-test only)

`dev-utils-test` uses `python-test` as its base image. If you are setting up
`dev-utils-test`, build `python-test` first:

```bash
cd ~/containers/python-test
docker compose up --build -d
```

Verify the image exists:
```bash
docker images python-test
```

You should see a `python-test` entry in the output. If you do not, the
`dev-utils-test` build will fail with a missing base image error.

---

## Step 5 — Build and start the container

### Isolated network (default)

No access to your LAN — internet via NAT only. Use this for general testing.

```bash
cd ~/containers/python-test        # or dev-utils-test
docker compose up --build
```

### LAN network

Full access to your host network — use when you need to reach LAN resources
such as a database server, other containers, or local services.

```bash
cd ~/containers/python-test        # or dev-utils-test
docker compose -f docker-compose.lan.yml up --build
```

> **Security note:** `network_mode: host` gives the container full access to
> your host network stack. Use only in trusted environments.

---

## Common commands

```bash
# Open a shell inside the running container
docker compose exec python-test bash
docker compose exec dev-utils-test bash

# Test setupkit is available (dev-utils-test only)
docker compose exec dev-utils-test setupkit --help

# Follow container logs
docker compose logs -f

# Stop and remove the container (keeps the image)
docker compose down

# Remove the image and rebuild from scratch
docker compose down --rmi local
docker compose up --build
```

---

## Rebuilding after updates

Container files are fetched once. To pick up changes from the repo, re-fetch
the files and rebuild:

```bash
cd ~/containers/python-test    # or dev-utils-test

BASE="https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/python-test"
curl -fsSL "${BASE}/Dockerfile"         -o Dockerfile
curl -fsSL "${BASE}/docker-compose.yml" -o docker-compose.yml

docker compose down --rmi local
docker compose up --build
```

Or re-run the setup script — it will ask before overwriting existing files.

---

## What the setup script does

`setup.sh` automates every step in this document:

1. Checks that `docker`, `docker compose`, `python3`, and `curl` are present
2. Fetches `containers.yaml` from the repo — this is the registry that drives
   all prompts and file lists; no container names or variables are hardcoded
   in the script itself
3. Validates the requested container name against the registry
4. Creates `~/containers/<name>/` if it does not exist
5. Prompts for each `.env` variable, showing auto-detected defaults
6. Writes `.env`
7. Fetches the container files listed in the registry
8. For containers with a base image dependency, checks whether that image
   exists locally and offers to build it if not
9. Offers to run `docker compose up --build`

To run it:
```bash
curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/setup-tests/setup.sh | bash -s python-test
curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/setup-tests/setup.sh | bash -s dev-utils-test
```

```
