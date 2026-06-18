# nmkit — Session Handoff

## What nmkit is

A cross-platform NoMachine connection launcher. PySide6 desktop app with
system tray, connection list, and Add/Edit/Delete/Connect UI. Designed
as a peer to pxkit in the dev-utils monorepo, with a shared install
convention and eventual guikit extraction planned.

Business context: nmkit is the remote support tool for the Windows EOL
migration consulting product. NoMachine was chosen over SPICE/RDP because
it's the only client that works reliably on macOS, Linux, and Windows without
per-platform configuration. Felipe (Chula Vista, hardware-focused) is a
potential pilot user.

---

## State at end of session

### What's working
- App launches with correct title "NX Launcher"
- Qt Designer layout (nmLauncher.ui) integrated successfully
- QListView replaced by QListWidget programmatically (same geometry)
- Connection list populates with Tux/FA glyph icons per OS hint
- Single click selects item, updates Current Connection header with
  name and description
- Add connection dialog opens, saves, list refreshes immediately
- Edit connection dialog opens pre-populated, saves correctly
- Delete works with confirmation dialog, list refreshes
- Right-click context menu: Connect / View Details / Edit / Delete
- Double-click on list item triggers connect attempt
- System tray: Show / Quit / Force Quit
- Font Awesome .otf assets download on first run, icons look great
- pylint 10.00/10 (generated files excluded)
- pytest 84/84 passing

### What's not working
- **Connect does not launch nxplayer** — root cause identified at end
  of session (see below). Fix is straightforward, not yet implemented.

### Connect root cause identified
nxplayer requires `.nxs` files to exist in `~/Documents/NoMachine/`.
nmkit currently writes temp `.nxs` files to `/tmp/` via
`tempfile.NamedTemporaryFile`. nxplayer cannot read them there.

**Fix:** Change `launcher.py` to write `.nxs` files to
`~/Documents/NoMachine/` instead of `/tmp/`. This directory already
exists (NoMachine creates it). Files can be persistent (one per
connection, named by connection name) or cleaned up after launch.

Confirmed by testing nxplayer directly:
```bash
/usr/NX/bin/nxplayer --config ~/Documents/NoMachine/Rocky.nxs
# ERROR: file does not exist — Rocky.nxs was not there
```
NoMachine's own session files live in `~/Documents/NoMachine/` and
nxplayer reads from there.

**Future enhancement:** Generate/regenerate `.nxs` files from YAML
config — nmkit already has all the data, just needs to render the
template and save persistently. One `.nxs` per connection entry.

### UI issues
- Default startup window size is too small — needs
  `self._window.resize(600, 500)` or similar after setCentralWidget
- Scrollbar appears on list due to slight size mismatch — will resolve
  with window size fix
- Maximized view looks great

---

## Next session priorities

1. **Fix connect** — change `_NX_SESSION_DIR` in `launcher.py` to
   `Path.home() / "Documents" / "NoMachine"`, write `.nxs` there,
   test connect button
2. **Fix default window size** — one line in `ui.py`
3. **Cross-platform path detection** — nxplayer binary path and session
   dir are different per OS; detect at runtime rather than hardcoding

---

## Cross-platform status

PySide6, requests, pyyaml, and Font Awesome all work on Linux/macOS/Windows.
The only platform-specific pieces:

| Component | Linux | macOS | Windows |
|---|---|---|---|
| nxplayer path | `/usr/NX/bin/nxplayer` | `/Applications/NoMachine.app/Contents/MacOS/nxplayer` | `C:\Program Files\NoMachine\bin\nxplayer.exe` |
| Session dir | `~/Documents/NoMachine/` | `~/Documents/NoMachine/` | `%USERPROFILE%\Documents\NoMachine\` |
| install.sh | works | works | needs Python installer |

`Path.home() / "Documents" / "NoMachine"` already works on all three
platforms. nxplayer path needs runtime detection in `config.py` or
`launcher.py`. `install.sh` needs a `install.py` equivalent for Windows.

PyInstaller can bundle into standalone executables per platform.

---

## Architecture

```
nmkit/
├── docs/
│   ├── change/                  # changedocs for each set of changes
│   └── project_structure.md
├── src/
│   └── nmkit/
│       ├── __init__.py
│       ├── __main__.py          # entry point, assets check, config, dispatch
│       ├── assets.py            # FA font download with dynamic zip discovery
│       ├── config.py            # loads nmkit.yaml + connections.yaml
│       ├── connection_dialog.py # Add/Edit/View Details dialog (pure PySide6)
│       ├── connEdit_ui.py       # GENERATED — unused, delete when convenient
│       ├── nmLauncher_ui.py     # GENERATED — do not edit, gitignored
│       ├── exceptions.py        # NmkitError hierarchy
│       ├── icons.py             # QPainter OS-hint icons, tray icon
│       ├── launcher.py          # generates .nxs, calls nxplayer --config
│       ├── logger.py            # rotating file + stderr handlers
│       ├── ui.py                # main window wrapping nmLauncher_ui
│       └── data/
│           ├── nmkit.yaml       # shipped app config defaults
│           ├── connections.yaml # shipped example connections
│           ├── fonts/           # FA .otf files (downloaded at runtime, gitignored)
│           └── qt_designs/
│               ├── connEdit.ui      # reference only
│               └── nmLauncher.ui    # active — recompile with pyside6-uic
├── tests/
│   ├── __init__.py
│   ├── test_assets.py
│   ├── test_config.py
│   ├── test_icons.py
│   └── test_launcher.py
├── install.sh
└── pyproject.toml
```

---

## Environment

| Item | Detail |
|---|---|
| Primary dev machine | MX Linux (wcyjv10) |
| Repo | `~/projects/dev-utils/python/nmkit` |
| Install location | `~/.local/share/nmkit/` |
| Symlink | `~/.local/bin/nmkit` |
| Config | `~/.config/nmkit/` (future: `~/.config/dev-utils/nmkit/`) |
| Log | `~/.local/share/nmkit/nmkit.log` |
| nxplayer binary | `/usr/NX/bin/nxplayer` |
| NoMachine session dir | `~/Documents/NoMachine/` |
| venv | `~/projects/dev-utils/python/nmkit/.venv` |
| Run tests | `python3 -m pytest` (not bare `pytest` — PATH issue) |
| Lint | `pylint ./src/` |
| Recompile UI | `.venv/bin/pyside6-uic src/nmkit/data/qt_designs/nmLauncher.ui -o src/nmkit/nmLauncher_ui.py` |

---

## Roadmap

- Fix connect (nxplayer session dir) — next session first task
- Default window size fix
- Cross-platform nxplayer path detection
- Persistent .nxs generation from YAML (one file per connection)
- GitHub Actions workflow: lint + test matrix (Linux/macOS/Windows),
  PyInstaller builds on tagged releases
- guikit extraction (once nmkit stable — shared Qt patterns with pxkit)
- logkit extraction (logger.py identical across kits)
- customerkit (headscale authkey UI for live USB demo)
- Customer portal (PHP/nginx/Docker on Hetzner VPS)
  - Public site: help docs, downloads
  - Customer portal: microblog, support tickets, schedule a call
  - Headscale authkey endpoint for customerkit
- dev-utils installer update (newer kits not registered)
- Forms library in dev-utils (`forms/<kitname>/` for .ui source files)
- install.py for Windows (replace bash install.sh)

---

## Key learnings this session

### nxplayer requires ~/Documents/NoMachine/ for session files
nxplayer cannot read .nxs files from /tmp/. Files must be in the
NoMachine session directory. This was the root cause of connect never
working despite the button firing correctly.

### QListWidget beats custom card grid
Custom card grid had fatal event routing problems. QListWidget with
setIcon() gives 90% of the visual result with none of the pain.

### Qt Designer for layout, code for logic
Designer owns the skeleton, code owns everything that changes at runtime.
The right split for this kind of app.

### Generated files must be gitignored and pylint-excluded
nmLauncher_ui.py and connEdit_ui.py are generated artifacts. Neither
should be committed or linted.

### Path.home() / "Documents" / "NoMachine" is cross-platform
Works correctly on Linux, macOS, and Windows without any platform
detection needed.
