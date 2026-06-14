# pxkit — Session Handoff

## State at end of session

### What's working
- GUI launches and minimizes to system tray correctly (Qt rewrite complete)
- `QSystemTrayIcon` replaces pystray — native, no background thread, restore works
- "Open Proxmox UI" button works
- VM buttons reach Proxmox API, retrieve SPICE tickets, and launch remote-viewer
- SPICE console opens successfully on both T490 and MX Linux
- Keyring integration working on both machines (kwallet on T490, kwallet on MX)
- Install script fully automated: config prompts, keyring store, PATH setup, wipe option
- Verbose/normal/quiet logging implemented (`pxkit -v`, `pxkit -q`, `log_level:` in yaml)
- Test suite: 50 tests, all passing

### Key fix this session: stdin pipe for SPICE launch
The critical bug was a ticket expiry race condition. The original approach wrote
the .vv file to a temp file, then launched remote-viewer on it. By the time
remote-viewer connected, the SPICE ticket had expired.

Fix: pipe .vv content directly to remote-viewer via stdin:
```python
process = subprocess.Popen(["remote-viewer", "-"], stdin=subprocess.PIPE, ...)
process.stdin.write(vv_content.encode("utf-8"))
process.stdin.close()
```
No temp file, no expiry window. Debug copy of .vv only written when `-v` is active.

### Key fix: _format_vv pass-through
Earlier sessions attempted to reformat the Proxmox API response — replacing
the host field, injecting type=, unescaping ca newlines. All wrong.

The correct approach: pass the API response through as-is. The Proxmox .vv
format is exactly what remote-viewer expects. Only the [virt-viewer] header
is added; everything else is untouched.

Reference working .vv (from Proxmox web UI download) is in the repo at
`docs/pve-spice-reference.vv` — use it as the spec for any future .vv work.

**New project rule added:** When generating file content for external
applications, always work from a confirmed working example first. Do not
infer format from docs or API responses.

---

## Environment

| Item | Detail |
|---|---|
| Primary dev machine | MX Linux (wcyjv10) |
| Test machine | Lenovo T490 (wcyjl1) — Proxmox VE 8.4 host with XFCE |
| Install location | `~/.local/share/pxkit/` |
| Symlink | `~/.local/bin/pxkit` |
| Log | `~/.local/share/pxkit/pxkit.log` |
| Debug .vv copy | `~/.local/share/pxkit/last-spice.vv` (verbose mode only) |
| Autostart | `~/.config/autostart/pxkit.desktop` |
| Keyring service | `pxkit` / token `carolyn@pam!pxkit` |
| Proxmox node | `wcyjl1` |
| Test VMs | 100 (Puppy Linux — off), 101 (Debian XFCE — autostart), 102 (Rocky Linux) |
| Repo | `~/projects/dev-utils/python/pxkit` (monorepo subdir) |

---

## Keyring setup

### T490 (wcyjl1)
- kwallet with GPG encryption
- kwalletd5 autostart via `~/.config/autostart/kwalletd5.desktop`
- PAM configured in `/etc/pam.d/lightdm`
- `qdbus org.kde.kwalletd5 /modules/kwalletd5` confirms D-Bus registration

### MX Linux (wcyjv10)
- kwallet with GPG encryption (gnome-keyring removed)
- kwalletd5 autostart via `~/.config/autostart/kwalletd5.desktop`
- PAM configured in `/etc/pam.d/lightdm` (gnome-keyring lines removed)
- Full setup documented in `docs/kwallet-setup-mx-linux.md`

---

## Priorities for next session

### 1. Mesh VM SPICE via WireGuard (first priority)
WireGuard tunnel through DigitalOcean droplet gives ThinkCentre a mesh address.
If WireGuard is in place, ThinkCentre VMs are reachable directly by mesh IP —
no SSH tunnel needed, pxkit just uses the mesh IP as host.

Discussion at end of session: WireGuard is the cleanest path. Assess WireGuard
status first. If not ready, implement SSH tunnel as interim.

Config for mesh VM (WireGuard path):
```yaml
- name: ThinkCentre Debian
  vmid: 203
  connection:
    type: spice
    host: 100.64.x.x   # WireGuard mesh address
    port: ~
    security: ~         # direct connection via mesh, no tunnel needed
```

Config for mesh VM (SSH tunnel path):
```yaml
- name: ThinkCentre Debian
  vmid: 203
  connection:
    type: spice
    host: 100.64.x.x
    port: ~
    security:
      method: ssh_tunnel
      key: ~/.ssh/keys/thinkcentre/spice
```

`_resolve_proxy()` already handles the ssh_tunnel case (returns localhost).
The tunnel setup itself is not yet implemented in launcher.py.

### 2. SSH terminal launch
`launch_ssh()` stub exists, raises "not yet implemented". Needs:
- Build SSH command from vm connection config (host, user, key)
- Invoke configured terminal emulator (from config)
- Consider: open tunnel first if security.method == ssh_tunnel

### 3. Fix remaining test gaps
- `test_raises_when_no_keyring_backend` in test_connection.py passes but
  requires NoKeyringError catch in connection.py (already implemented)
- Consider adding integration-style test for the stdin pipe flow

### 4. Systemd autostart option
See roadmap. Detect systemd, prompt user, write service file or desktop file.
Add `autostart: systemd|xdg` to pxkit.yaml.

### 5. Move to standalone repo
Currently in dev-utils monorepo. Creates confusion with git submodule warnings
during `git add`. Move to own repo when stable.

---

## Files changed this session

| File | Change |
|---|---|
| `src/pxkit/ui.py` | Full rewrite: tkinter → PySide6, QSystemTrayIcon |
| `src/pxkit/launcher.py` | stdin pipe for SPICE; launch_ssh stub; debug copy gated behind -v |
| `src/pxkit/connection.py` | _format_vv: pass-through; NoKeyringError catch; debug logging |
| `src/pxkit/logger.py` | verbose/normal/quiet verbosity levels |
| `src/pxkit/__main__.py` | -v/-q flags; log_level from yaml; _resolve_verbosity |
| `src/pxkit/data/pxkit.yaml` | type: spice added to all VM connection blocks; log_level key |
| `install.sh` | Full hardening: config prompts, keyring store, PATH, wipe option, progress output |
| `pyproject.toml` | PySide6, secretstorage, jeepney; removed pystray, Pillow; dev extras |
| `tests/test_launcher.py` | Full rewrite for stdin pipe approach |
| `tests/test_connection.py` | Updated for pass-through _format_vv; NoKeyringError test |
| `docs/roadmap.md` | Updated |
| `docs/system-footprint.md` | Updated dependencies |
| `docs/kwallet-setup-mx-linux.md` | New — full kwallet GPG setup procedure for XFCE |
| `project_rules.md` | New rule: work from confirmed working examples for external file formats |

---

## Key learnings this session

### SPICE ticket expiry
SPICE tickets are short-lived (30-60 seconds) by design. Any latency between
ticket retrieval and remote-viewer connecting can cause expiry. Stdin pipe
eliminates the temp file write and removes the race entirely.

### .vv file format
Proxmox returns the .vv content exactly as remote-viewer expects it. Do not
reformat, reorder, or transform the API response. Pass it through as-is.
The ca= field contains literal \n separators — leave them alone.

### kwallet on non-KDE desktops
kwallet requires a KDE session manager to register on D-Bus. On XFCE:
- PAM integration alone is not sufficient
- Must add kwalletd5 to XDG autostart with a .desktop file
- gnome-keyring must be removed (it blocks D-Bus registration)
- Full procedure documented in kwallet-setup-mx-linux.md

### Blog post ideas identified
- "Why your SPICE ticket keeps expiring and the stdin pipe fix"
- kwallet on XFCE with GPG encryption setup

---

## Install script state
install.sh is at a good functional state. Known remaining issues:
- `--wipe` correctly removes config but doesn't remove the keyring secret
  (by design — secrets are the user's to manage)
- Reinstall on existing machine skips config prompts (correct — leaves
  existing config alone) but also skips keyring prompt (may want to offer
  re-entry)
