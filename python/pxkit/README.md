# pxkit

> This package lives in the [dev-utils](https://github.com/carolynboyle/dev-utils)
> monorepo alongside several other tools. See the
> [top-level README](https://github.com/carolynboyle/dev-utils#readme) for the full
> picture. pxkit will move to its own repo in a future release.

A tkinter launcher for Proxmox VE. Provides one-click access to VM consoles
and the Proxmox web UI from a small desktop window. Designed for portable demo
machines and small business server deployments.

Connects to local VMs via SPICE and remote VMs over SSH tunnels. SSH terminal
support is on the roadmap.

---

## Requirements

- Python 3.11+
- Proxmox VE 8.x with an API token
- A SecretService-compatible keyring (kwallet, GNOME Keyring) for token storage
- `virt-viewer` for SPICE console access (installed automatically by `install.sh`)

---

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/python/pxkit/install.sh | bash
```

The installer will prompt for an install location, offer to set up autostart,
and print instructions for storing your API token secret.

Python 3.11+ and `git` are required. `virt-viewer` will be installed
automatically if not already present (requires `apt`, `dnf`, or `pacman`).

### Installing for development

To work on pxkit directly:

```bash
git clone https://github.com/carolynboyle/dev-utils.git
cd dev-utils/python/pxkit
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Configuration

Copy the default config to get started:

```bash
mkdir -p ~/.config/pxkit
cp src/pxkit/data/pxkit.yaml ~/.config/pxkit/pxkit.yaml
```

Edit `~/.config/pxkit/pxkit.yaml` with your Proxmox host, node name, token ID,
and VM list. You only need to include the keys you want to override — the
shipped defaults fill in the rest.

See [docs/configuration.md](docs/configuration.md) for the full config reference.

---

## Secrets setup

The API token secret is never stored in the config file. Store it in your
system keyring before running pxkit:

```python
import keyring
keyring.set_password("pxkit", "your-token-id@pam!pxkit", "your-token-secret")
```

Run this once from a Python shell with your venv active. pxkit retrieves it at
runtime via SecretService. See [docs/secrets.md](docs/secrets.md) for kwallet
setup details.

---

## Usage

Launch the GUI:

```bash
pxkit
```

CLI commands (no GUI):

```bash
pxkit launch "VM Name"   # launch a VM console by name
pxkit ui                 # open the Proxmox web UI in the default browser
```

---

## Further reading

- [docs/configuration.md](docs/configuration.md) — full config file reference
- [docs/secrets.md](docs/secrets.md) — kwallet/SecretService setup
- [docs/architecture.md](docs/architecture.md) — module overview for developers
- [docs/roadmap.md](docs/roadmap.md) — planned features
- [docs/system-footprint.md](docs/system-footprint.md) — everything the installer and runtime add to your system
