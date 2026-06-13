# pxkit — Session Handoff

## What pxkit is

A Python package that lives in the `dev-utils` repo under `python/pxkit/`. It provides a small tkinter dialog that launches on XFCE login and gives one-click access to:

- The Proxmox web UI (opens in Chrome)
- Each configured VM's SPICE console (launches via `remote-viewer`)

Primary use case: T490 laptop running Proxmox with XFCE desktop, used as a portable client demo machine. The launcher is a demo piece — it shows off the capability of running multiple VMs on a single portable machine.

Designed to expand to mesh network VMs (ThinkCentre and others) via the same YAML config structure.

---

## Infrastructure completed this session

### KWallet + SecretService
- `kwalletmanager5` installed on T490 (Debian 12 / Proxmox host with XFCE)
- GPG key generated (RSA 4096, no expiry), backed up to Proton Drive at `whycantyoujust.tech/secure/`
- kwallet database `t490_local` created with GPG encryption
- `libpam-kwallet5` installed and configured in `/etc/pam.d/lightdm` — kwallet auto-unlocks at login
- SecretService confirmed live on D-Bus at login: `org.freedesktop.secrets`
- `python3-keyring` installed and confirmed talking to kwallet via SecretService

### Proxmox API Token
- Token `carolyn@pam!pxkit` created in Proxmox
- Privilege separation enabled
- `PVEVMUser` role assigned to token on `/vms`
- Token secret stored in kwallet: `keyring.set_password("pxkit", "carolyn@pam!pxkit", ...)`
- API access confirmed working against `https://localhost:8006/api2/json/nodes`

### pxkit repo structure
- Created via treekit from `pxkit-structure.md`
- Lives at `python/pxkit/` in dev-utils repo (or standalone repo TBD)

---

## Design decisions

### Architecture
- Follows dev-utils kit conventions: OOP, small modules, no hardcoded values
- YAML config drives everything — labels, VM list, connection details
- Config hierarchy: shipped `data/pxkit.yaml` → user overrides in `~/.config/pxkit/`
- CLI parity required (project rules): `pxkit launch <vm-name>` must work from terminal
- GUI is a visualizer only — no logic in `ui.py`

### Module responsibilities
| Module | Responsibility |
|---|---|
| `config.py` | Load and validate YAML, apply user overrides |
| `connection.py` | Proxmox API calls, SPICE ticket retrieval, connection strategy (local vs SSH tunnel) |
| `launcher.py` | Open Chrome to Proxmox URL, invoke `remote-viewer` with SPICE ticket |
| `ui.py` | tkinter dialog, calls launcher only, owns no logic |
| `__main__.py` | Entry point |
| `data/pxkit.yaml` | Shipped defaults and example config |

### YAML config shape
```yaml
proxmox:
  host: localhost
  port: 8006
  node: wcyjl1
  token_id: carolyn@pam!pxkit
  # token secret lives in kwallet only, never in config

vms:
  - name: Puppy Linux
    vmid: 100
    connection:
      host: localhost
      port: ~
      security: ~

  - name: Debian XFCE
    vmid: 101
    connection:
      host: localhost
      port: ~
      security: ~

  - name: Rocky Linux
    vmid: 102
    connection:
      host: localhost
      port: ~
      security: ~

  # mesh example (future)
  # - name: ThinkCentre Debian
  #   vmid: 203
  #   connection:
  #     host: 192.168.x.x
  #     port: ~
  #     security:
  #       method: ssh_tunnel
  #       key: ~/.ssh/keys/thinkcentre/spice
```

### Secrets handling
- Token secret retrieved at runtime via `keyring.get_password("pxkit", "carolyn@pam!pxkit")`
- kwallet is the SecretService backend
- No secrets ever in YAML or code

### SPICE launch flow
1. Call Proxmox API with token → get SPICE ticket (`.vv` content)
2. Write to temp file
3. Launch `remote-viewer` on temp file
4. Clean up temp file

### Security field in YAML
- `security: ~` = direct connection, no auth (local VMs)
- `security.method: ssh_tunnel` = SSH tunnel (mesh VMs, future)
- Launcher checks security field and sets up tunnel before connecting if needed

---

## Known issues / deferred items

- **Print Screen key broken** — KeePassXC flatpak install grabbed the shortcut and didn't release it on uninstall. Fix: reassign in XFCE Settings → Keyboard → Application Shortcuts. Deferred.
- **KeePassXC abandoned** — Debian 12 package has broken D-Bus/SecretService. Flatpak version also failed to register. kwallet used instead.
- **SSH reliability** — ssh-agent silent failure on Hetzner VPS led to 3-day debug session and VPS rebuild. Root cause: agent offering wrong keys without `IdentitiesOnly yes`. Fix pending: add `IdentitiesOnly yes` to all `~/.ssh/config` host blocks, consider KWallet SSH agent integration.

---

## Immediate next steps for pxkit

1. Write `data/pxkit.yaml` — shipped defaults with the three local VMs
2. Write `config.py` — YAML loader with user override support
3. Write `connection.py` — Proxmox API call to get SPICE ticket
4. Write `launcher.py` — Chrome open + remote-viewer launch
5. Write `ui.py` — tkinter dialog
6. Write `__main__.py` — entry point, wires everything together
7. Write tests for config, connection, launcher
8. Write `pyproject.toml`
9. Test XFCE autostart via Session and Startup

---

## Environment

| Item | Detail |
|---|---|
| Machine | Lenovo T490 |
| OS | Debian 12 (Proxmox VE 8.4.19 host with XFCE) |
| Proxmox node | `wcyjl1` |
| API endpoint | `https://localhost:8006` |
| VMs | 100 (Puppy), 101 (debian-x), 102 (wcyjv15) |
| Secrets backend | kwallet5 + GPG |
| Python keyring | `python3-keyring` (apt) |
| Token | `carolyn@pam!pxkit` in kwallet service `pxkit` |
