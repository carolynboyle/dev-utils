# nmkit — platform.yaml and open_command

## Summary

Introduces `platform.yaml` to hold all platform-specific paths and
commands. OS detection happens at startup; `config.platform` exposes
flat, resolved values for the current OS so no caller ever inspects
`sys.platform` directly. `launcher.py` switches from calling nxplayer
directly to using the platform `open_command` (xdg-open on Linux),
which correctly opens the specific connection rather than the NoMachine
main window. Window minimum size fixed to eliminate the negative size
Qt warning.

---

## platform.yaml (NEW)

**Path:** `src/nmkit/data/platform.yaml`

New shipped default. Contains all platform-specific paths and commands,
nested by OS key (linux / darwin / windows). User override at
`~/.config/nmkit/platform.yaml` — only keys to change need be present.

Keys: `open_command`, `nxplayer`, `terminal`.

---

## nmkit.yaml

**Path:** `src/nmkit/data/nmkit.yaml` AND `~/.config/nmkit/nmkit.yaml`

### Change 1 — Remove nxplayer, terminal keys; update comment block

**Why:** `nxplayer` and `terminal` are platform-specific and now live
in `platform.yaml`. `nmkit.yaml` is now pure app config.

**BEFORE:**
```yaml
nmkit:
  nxplayer: /usr/NX/bin/nxplayer
  session_dir: ~/Documents/NoMachine
  terminal:
    app: xfce4-terminal
    exec_flag: -e
  ui:
    title: NX Launcher
  log_level: normal
```

**AFTER:**
```yaml
nmkit:
  session_dir: ~/Documents/NoMachine
  ui:
    title: NX Launcher
  log_level: normal
```

---

## config.py

**Path:** `src/nmkit/config.py`

### Change 2 — Add platform config paths

**Why:** New paths needed for default and user platform.yaml files.

**BEFORE:**
```python
_DATA_DIR            = Path(__file__).parent / "data"
_DEFAULT_APP_CONFIG  = _DATA_DIR / "nmkit.yaml"
_DEFAULT_CONNECTIONS = _DATA_DIR / "connections.yaml"
_USER_CONFIG_DIR     = Path.home() / ".config" / "nmkit"
_USER_APP_CONFIG     = _USER_CONFIG_DIR / "nmkit.yaml"
_USER_CONNECTIONS    = _USER_CONFIG_DIR / "connections.yaml"
```

**AFTER:**
```python
_DATA_DIR                = Path(__file__).parent / "data"
_DEFAULT_APP_CONFIG      = _DATA_DIR / "nmkit.yaml"
_DEFAULT_PLATFORM_CONFIG = _DATA_DIR / "platform.yaml"
_DEFAULT_CONNECTIONS     = _DATA_DIR / "connections.yaml"
_USER_CONFIG_DIR         = Path.home() / ".config" / "nmkit"
_USER_APP_CONFIG         = _USER_CONFIG_DIR / "nmkit.yaml"
_USER_PLATFORM_CONFIG    = _USER_CONFIG_DIR / "platform.yaml"
_USER_CONNECTIONS        = _USER_CONFIG_DIR / "connections.yaml"
```

### Change 3 — Add _PLATFORM_MAP

**Why:** Maps sys.platform values to platform.yaml OS keys. win32 is
Python's value for all Windows regardless of bitness.

**AFTER:**
```python
_PLATFORM_MAP = {
    "linux":  "linux",
    "darwin": "darwin",
    "win32":  "windows",
}
```

### Change 4 — Add platform_config_path to __init__; call _detect_platform and _load_platform

**Why:** ConfigManager now loads and exposes platform config alongside
app config and connections.

**BEFORE:**
```python
    def __init__(
        self,
        app_config_path: Optional[Path] = None,
        connections_path: Optional[Path] = None,
    ):
        self._app         = self._load_app(app_config_path)
        self._connections = self._load_connections(connections_path)
```

**AFTER:**
```python
    def __init__(
        self,
        app_config_path: Optional[Path] = None,
        platform_config_path: Optional[Path] = None,
        connections_path: Optional[Path] = None,
    ):
        self._os_key      = self._detect_platform()
        self._app         = self._load_app(app_config_path)
        self._platform    = self._load_platform(platform_config_path)
        self._connections = self._load_connections(connections_path)
```

### Change 5 — Add platform property

**Why:** Exposes resolved platform config to callers.

**AFTER:**
```python
    @property
    def platform(self) -> dict:
        """Resolved platform settings for the current OS."""
        return self._platform
```

### Change 6 — Add _detect_platform, _load_platform, _resolve_platform

**Why:** Core platform config logic. `_detect_platform` maps
`sys.platform` to a yaml key and raises on unsupported OS.
`_load_platform` merges default and user files. `_resolve_platform`
selects the value for the current OS from each nested key, returning
a flat dict.

---

## launcher.py

**Path:** `src/nmkit/launcher.py`

### Change 7 — Read open_command and nxplayer from config.platform in __init__

**Why:** Both values are now platform-specific and live in platform.yaml.

**BEFORE:**
```python
    def __init__(self, config):
        self._nxplayer    = config.app.get("nxplayer", "/usr/NX/bin/nxplayer")
        session_dir_raw   = config.app.get("session_dir", "~/Documents/NoMachine")
        self._session_dir = Path(session_dir_raw).expanduser()
```

**AFTER:**
```python
    def __init__(self, config):
        self._open_command = config.platform.get("open_command", "xdg-open")
        self._nxplayer     = config.platform.get("nxplayer", "/usr/NX/bin/nxplayer")
        session_dir_raw    = config.app.get("session_dir", "~/Documents/NoMachine")
        self._session_dir  = Path(session_dir_raw).expanduser()
```

### Change 8 — Replace _start_nxplayer(nxs_path) with _open_session(nxs_path)

**Why:** Calling nxplayer directly with --config opens the NoMachine
main window rather than the specific connection. Using the platform
open command (xdg-open on Linux) hands the .nxs file to NoMachine's
file association handler, which opens the connection correctly.
Confirmed working by manual test.

`startfile` is handled as a special case using `os.startfile()` since
it is not a subprocess call.

### Change 9 — _start_nxplayer() now takes no arguments

**Why:** Retained for future "Open NoMachine" tray menu option. Launches
the NoMachine main window directly, no session file needed.

### Change 10 — launch() calls _open_session instead of _start_nxplayer

**BEFORE:**
```python
    def launch(self, connection: dict) -> None:
        nxs_content = self._render_nxs(connection)
        nxs_path    = self._write_nxs(nxs_content, connection["name"])
        self._start_nxplayer(nxs_path)
```

**AFTER:**
```python
    def launch(self, connection: dict) -> None:
        nxs_content = self._render_nxs(connection)
        nxs_path    = self._write_nxs(nxs_content, connection["name"])
        self._open_session(nxs_path)
```

---

## ui.py

**Path:** `src/nmkit/ui.py`

### Change 11 — Fix negative minimum window size

**Why:** `self._window.setMinimumSize(self._central.sizeHint())` was
returning (-1, -1) because sizeHint() was called before layout
completion. Qt logged: `Widget::setMinimumSize: Negative sizes (-1,-1)
are not possible`. Replaced with explicit pixel values. Added
`adjustSize()` call after `show()` so the window fits its content on
first open.

**BEFORE:**
```python
        self._window.setMinimumSize(self._central.sizeHint())
```
(no adjustSize in run())

**AFTER:**
```python
        self._window.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
```
```python
    def run(self) -> int:
        self._window.show()
        self._window.adjustSize()
        return self._app.exec()
```

Constants added:
```python
_MIN_WIDTH   = 500  # px — minimum window width
_MIN_HEIGHT  = 400  # px — minimum window height
```

---

## install.sh

**Path:** `install.sh`

### Change 12 — Copy platform.yaml in setup_config

**Why:** `platform.yaml` is a new config file that users may want to
override (e.g. non-standard nxplayer path). Copied alongside
nmkit.yaml and connections.yaml on fresh install.

**BEFORE:**
```bash
    if [[ -f "$data_dir/nmkit.yaml" ]]; then
        cp "$data_dir/nmkit.yaml" "$CONFIG_DIR/nmkit.yaml"
        ok "Copied default nmkit.yaml to $CONFIG_DIR/"
    fi

    if [[ -f "$data_dir/connections.yaml" ]]; then
        ...
```

**AFTER:**
```bash
    if [[ -f "$data_dir/nmkit.yaml" ]]; then
        cp "$data_dir/nmkit.yaml" "$CONFIG_DIR/nmkit.yaml"
        ok "Copied default nmkit.yaml to $CONFIG_DIR/"
    fi

    if [[ -f "$data_dir/platform.yaml" ]]; then
        cp "$data_dir/platform.yaml" "$CONFIG_DIR/platform.yaml"
        ok "Copied default platform.yaml to $CONFIG_DIR/"
    fi

    if [[ -f "$data_dir/connections.yaml" ]]; then
        ...
```

---

## test_config.py

**Path:** `tests/test_config.py`

### Change 13 — Add MINIMAL_PLATFORM_YAML fixture and update make_config

**Why:** make_config now needs to write and patch platform.yaml paths,
and patch sys.platform so tests run independently of the host OS.

### Change 14 — Add TestPlatformConfigLoading class

Tests cover: open_command resolution per OS, nxplayer path resolution,
terminal resolution, user override merging, and unsupported platform
error.

### Change 15 — Remove nxclient/nxplayer references from app config tests

**Why:** These keys no longer live in nmkit.yaml. App config tests now
cover session_dir, ui, log_level only.

---

## test_launcher.py

**Path:** `tests/test_launcher.py`

### Change 16 — Add platform property to make_mock_config

**Why:** Launcher now reads open_command and nxplayer from
config.platform, not config.app.

**BEFORE:**
```python
def make_mock_config(nxplayer="/usr/NX/bin/nxplayer", session_dir=None):
    app_dict = {
        "nxplayer":    nxplayer,
        "session_dir": str(session_dir) if session_dir else "/tmp/nmkit-test",
    }
    config           = MagicMock()
    type(config).app = PropertyMock(return_value=app_dict)
    return config
```

**AFTER:**
```python
def make_mock_config(
    open_command="xdg-open",
    nxplayer="/usr/NX/bin/nxplayer",
    session_dir=None,
):
    app_dict = {
        "session_dir": str(session_dir) if session_dir else "/tmp/nmkit-test",
    }
    platform_dict = {
        "open_command": open_command,
        "nxplayer":     nxplayer,
    }
    config                = MagicMock()
    type(config).app      = PropertyMock(return_value=app_dict)
    type(config).platform = PropertyMock(return_value=platform_dict)
    return config
```

### Change 17 — Replace TestStartNxplayer with TestOpenSession; retain TestStartNxplayer

**Why:** `_open_session` is the method called by `launch()`. Tests cover
xdg-open subprocess call, FileNotFoundError, OSError, startfile special
case, detached launch, and open_command from config. `TestStartNxplayer`
is updated to reflect that `_start_nxplayer()` now takes no arguments.
