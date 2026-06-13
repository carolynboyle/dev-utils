# pxkit — Session Handoff

## State at end of session

### What's working
- GUI launches and autostarts on login via XFCE autostart
- "Open Proxmox UI" button works correctly
- VM buttons appear, are clickable, and reach the Proxmox API successfully
- Keyring/kwallet integration working once kwalletd5 is on D-Bus
- Install script functional for core flow (git, venv, dependencies)

### What's not working
1. **VM SPICE launch** — remote-viewer shows "Cannot determine the connection
   type from URI". The API call succeeds and a .vv file is being written, but
   something in the .vv content is still wrong.
2. **System tray restore** — window minimizes to tray but clicking the tray
   icon does not restore it. pystray threading issues suspected.

### Decision made: switching ui.py from tkinter to PySide6 (Qt)
Tkinter system tray support via pystray has proven unreliable. Qt's
`QSystemTrayIcon` is native, well-documented, and solid. PySide6 is the
official Qt binding (LGPL), actively maintained, and brings everything needed
in one package. Time spent on the Qt rewrite is expected to be less than
debugging the pystray threading issues.

---

## Priorities for next session

### 1. Rewrite ui.py in PySide6 (first priority)
Replace the tkinter/pystray implementation with PySide6. Key changes:

- `QApplication` replaces `tk.Tk()`
- `QMainWindow` or `QWidget` for the main window
- `QSystemTrayIcon` replaces pystray — native, no background thread needed
- `QVBoxLayout` + `QScrollArea` replaces Canvas/Scrollbar hack
- `QPushButton` replaces `tk.Button`
- `QMessageBox` replaces `tkinter.messagebox`

Qt Designer is installed on the T490 — can be used to prototype the layout
but the final implementation should be code-driven to stay consistent with
the kit conventions (no .ui files as external assets).

`pystray` and `Pillow` can be removed from `pyproject.toml` once Qt is in.
Add `PySide6` as the replacement dependency.

The tray icon can be generated programmatically using `QPixmap`/`QPainter`
(same blue #2196F3 as before) — no Pillow needed.

### 2. Debug SPICE launch (after Qt rewrite)
The .vv content fix is in the repo (`_format_vv` updated) but untested due
to the tray issue. Once Qt is working and the UI is stable, test SPICE launch.

Key things to verify in the .vv output:
- `type=spice` is present (from VM connection config, not hardcoded)
- `ca` field has real newlines not `\\n`
- `proxy` field is excluded
- Consider logging the .vv content at DEBUG level temporarily

### 3. Fix NoKeyringError handling in connection.py
Add a try/except around `keyring.get_password` to catch
`keyring.errors.NoKeyringError` and re-raise as `PxkitConnectionError`
with a clear message. Currently this exception type bypasses the
`PxkitConnectionError` handler in ui.py.

### 4. Add missing dependencies to pyproject.toml
- `secretstorage` — keyring SecretService backend
- `jeepney` — D-Bus pure-Python transport

Remove `pystray` and `Pillow` once Qt rewrite is done.

### 5. Update install script for system packages
These are apt packages (not pip) that the install script must handle:
- `python3.11-venv` — already handled
- `python3-tk` — add to install script (can be removed once Qt replaces tkinter)
- `python3-secretstorage` — add to install script

### 6. Write changedocs for this session's changes
- `connection.py` — `_format_vv()` updated: type from VM config, ca
  newlines unescaped, proxy field skipped; signature changed to
  `_format_vv(data, conn_type)`
- `ui.py` — broad `except Exception` block added to `_on_launch_vm`
- `install.sh` — multiple fixes: global vars, sudo credential caching,
  python3-venv install, git install
- `pyproject.toml` — secretstorage, jeepney to add; pystray, Pillow to
  remove after Qt rewrite

### 7. Update tests
- `test_connection.py` — `_format_vv` signature changed; update existing
  tests and add `test_raises_when_no_keyring_backend` to `TestGetTokenSecret`
- `test_ui.py` — will need to be written from scratch for PySide6

---

## Key discoveries this session

### kwallet/D-Bus issue
kwalletd5 sometimes starts without registering on D-Bus (`Lacking a socket,
pipe: 0 env: 0`). PAM integration is configured in `/etc/pam.d/lightdm`.
When it works, `org.freedesktop.secrets` appears on the D-Bus session bus.
When it doesn't, keyring raises `NoKeyringError`.
Workaround until fixed: `kwalletd5 &` manually, then restart pxkit.

### Proxmox spiceproxy response quirks
- Does NOT include `type=` field — must be added from VM config
- `ca` field contains `\\n` escaped newlines — must be unescaped to `\n`
- `proxy` field contains Proxmox's own proxy URL — must be skipped
- `host` field format: `pvespiceproxy:hash:vmid:node:port::fingerprint`

### install.sh bash gotcha
Functions that both print to stdout AND return a value via `echo` cannot
be called with `$(...)` command substitution — all stdout gets captured
into the variable. Fixed by using global variables (PYTHON, INSTALL_DIR)
instead of command substitution.

### Qt Designer on T490
Qt Designer is installed at `/usr/bin/designer` (or similar). Can be used
to prototype layouts but final ui.py should be code-driven.

---

## Files changed this session (in repo)

| File | Status |
|---|---|
| `src/pxkit/connection.py` | Updated — _format_vv fixed |
| `src/pxkit/ui.py` | Updated — broad except block added; will be rewritten in Qt |
| `src/pxkit/data/pxkit.yaml` | No changes |
| `install.sh` | Updated — multiple fixes |
| `pyproject.toml` | Needs secretstorage, jeepney; pystray/Pillow to remove after Qt |
| `tests/test_connection.py` | Needs _format_vv signature update + NoKeyringError test |
| `tests/test_ui.py` | Will need full rewrite for PySide6 |
| `docs/roadmap.md` | Created |
| `docs/system-footprint.md` | Created |

---

## Environment

| Item | Detail |
|---|---|
| Machine | Lenovo T490 (wcyjl1) |
| OS | Debian 12 / Proxmox VE 8.4.19 host with XFCE |
| Install location | `~/.local/share/pxkit/` |
| Symlink | `~/.local/bin/pxkit` |
| Log | `~/.local/share/pxkit/pxkit.log` |
| Autostart | `~/.config/autostart/pxkit.desktop` |
| Keyring service | `pxkit` / token `carolyn@pam!pxkit` |
| Proxmox node | `wcyjl1` |
| Test VMs | 100 (Puppy), 101 (debian-x), 102 (wcyjv15) |
| Qt Designer | Installed on T490 |
