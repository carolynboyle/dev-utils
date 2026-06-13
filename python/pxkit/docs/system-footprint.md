# pxkit — System Footprint

This document describes everything pxkit's installer and runtime add to your
system. Nothing happens outside this list.

---

## System packages

The installer will attempt to install the following via your system package
manager (`apt`, `dnf`, or `pacman`) if they are not already present. You will
be asked for your password if `sudo` is required.

| Package | Why |
|---|---|
| `git` | Required to download pxkit during installation |
| `virt-viewer` | Required for SPICE console access to VMs |
| `libxcb-cursor0` | Required by Qt 6.5+ xcb platform plugin (Debian/Ubuntu/MX) |
| `python3-secretstorage` | keyring SecretService backend (Debian/Ubuntu/MX) |
| `libsecret-1-0` | Runtime dependency of secretstorage (Debian/Ubuntu/MX) |

If your package manager is not detected, the installer will print manual
install instructions and continue. All packages are standard and widely
available. Equivalent packages exist on Fedora/Rocky and Arch — see
`install.sh` comments for exact names.

---

## Python dependencies

All Python dependencies are installed into a virtualenv at your chosen install
location. **Nothing is installed into system Python.**

| Package | Purpose |
|---|---|
| `pyyaml` | Reads the pxkit YAML config file |
| `requests` | Makes API calls to Proxmox |
| `keyring` | Retrieves the API token secret from your system keyring |
| `urllib3` | HTTP support for requests |
| `PySide6` | Qt bindings — GUI, system tray, all UI |
| `secretstorage` | keyring SecretService backend (pip component) |
| `jeepney` | D-Bus pure-Python transport (secretstorage dependency) |

---

## Files written to disk

| Path | What it is | When created |
|---|---|---|
| `~/.local/share/pxkit/` | Application source and virtualenv | During install |
| `~/.local/bin/pxkit` | Symlink to the pxkit command | During install |
| `~/.config/pxkit/pxkit.yaml` | Your personal config file | Only if you create it |
| `~/.config/autostart/pxkit.desktop` | XFCE/GNOME autostart entry | Only if you opt in |
| `~/.local/share/pxkit/pxkit.log` | Runtime log file | On first run |

All paths are within your home directory. No files are written outside `$HOME`.
No root access is required after system packages are installed.

---

## Keyring

One entry is written to your system keyring (kwallet, GNOME Keyring, or
equivalent) under:

- **Service:** `pxkit`
- **Username:** your Proxmox API token ID (e.g. `carolyn@pam!pxkit`)
- **Secret:** your Proxmox API token secret

This entry is written manually by you during setup — the installer prints
the exact command. pxkit reads it at runtime but never modifies or deletes it.

To remove it:

```python
import keyring
keyring.delete_password("pxkit", "your-token-id@pam!pxkit")
```

---

## What pxkit does NOT do

- Does not modify system Python or install packages outside the virtualenv
- Does not install system services or daemons
- Does not run any background processes outside your desktop session
- Does not make network connections except to your own Proxmox host at runtime
- Does not phone home, check for updates automatically, or send any telemetry
- Does not modify shell rc files (`~/.bashrc`, `~/.zshrc`) — PATH is handled
  via symlink to `~/.local/bin/`, which is on PATH by default on most
  modern Linux distributions

---

## Uninstalling

To remove pxkit completely:

```bash
# Remove application and venv
rm -rf ~/.local/share/pxkit

# Remove symlink
rm -f ~/.local/bin/pxkit

# Remove user config (optional — keep if you want to reinstall later)
rm -rf ~/.config/pxkit

# Remove autostart entry (if set up)
rm -f ~/.config/autostart/pxkit.desktop

# Remove keyring entry
python3 -c "import keyring; keyring.delete_password('pxkit', 'your-token-id')"
```

System packages (`git`, `virt-viewer`, `libxcb-cursor0`, etc.) are not
removed — they are standard packages that may be used by other software.
