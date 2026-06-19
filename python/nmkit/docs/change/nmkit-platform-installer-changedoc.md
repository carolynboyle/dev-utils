# nmkit — installer-based platform detection

## Summary

OS detection moved from runtime (config.py) to install time (install.sh).
The installer detects the platform via `uname`, extracts the correct
values from the nested `src/nmkit/data/platform.yaml`, and writes a flat
`~/.config/nmkit/platform.yaml` containing only the values for the
installed OS. config.py loads this flat file the same way it loads
nmkit.yaml — no OS detection logic needed at runtime.

---

## install.sh

**Path:** `install.sh`

### Change 1 — Add detect_platform step

**Why:** OS detection belongs at install time, not runtime. Uses `uname`
to identify the platform and errors out cleanly on unsupported systems.
Result stored in `$PLATFORM` global for use in setup_config.

**AFTER:**
```bash
detect_platform() {
    case "$(uname -s)" in
        Linux*)               PLATFORM="linux" ;;
        Darwin*)              PLATFORM="darwin" ;;
        MINGW*|CYGWIN*|MSYS*) PLATFORM="windows" ;;
        *)
            die "Unsupported platform: $(uname -s)."
            ;;
    esac
    ok "Detected platform: $PLATFORM"
}
```

### Change 2 — Generate flat platform.yaml in setup_config

**Why:** The shipped `platform.yaml` has nested OS keys. The user config
needs flat values for the installed OS only. A small inline Python
script extracts the correct section and writes the flat file.

**BEFORE:**
```bash
    if [[ -f "$data_dir/platform.yaml" ]]; then
        cp "$data_dir/platform.yaml" "$CONFIG_DIR/platform.yaml"
        ok "Copied default platform.yaml to $CONFIG_DIR/"
    fi
```

**AFTER:**
```bash
    if [[ -f "$data_dir/platform.yaml" ]]; then
        info "Generating platform.yaml for $PLATFORM..."
        "$INSTALL_DIR/venv/bin/python" - <<PYEOF
import yaml
from pathlib import Path
# ... reads nested platform.yaml, writes flat version for $PLATFORM
PYEOF
    fi
```

### Change 3 — Add detect_platform to main() call sequence

**Why:** Must run before setup_config so $PLATFORM is available.
Runs first, before find_python.

**BEFORE:**
```bash
    find_python
    check_nxplayer
    ...
```

**AFTER:**
```bash
    detect_platform
    find_python
    check_nxplayer
    ...
```

### Change 4 — Add $PLATFORM to global declarations

**Why:** Used by detect_platform and setup_config.

---

## config.py

**Path:** `src/nmkit/config.py`

### Change 5 — Remove sys import, _PLATFORM_MAP, _detect_platform, _resolve_platform

**Why:** OS detection is now the installer's responsibility. config.py
loads the flat user platform.yaml the same way it loads nmkit.yaml.
No runtime platform logic needed.

### Change 6 — Simplify _load_platform

**Why:** User platform.yaml is now flat — no resolution step needed.
Falls back to the shipped nested default with a warning if the user
file is absent (development scenario, installer not run).

**BEFORE:**
```python
    def _load_platform(self, config_path):
        # ... merged nested YAML, called _resolve_platform
        return self._resolve_platform(merged)
```

**AFTER:**
```python
    @staticmethod
    def _load_platform(config_path):
        user_path = config_path or _USER_PLATFORM_CONFIG

        if user_path.exists():
            user = ConfigManager._load_section(user_path, "platform")
            log.debug("Loaded user platform config from %s", user_path)
            return user

        log.warning(
            "No user platform config found at %s. "
            "Run the installer to generate a platform-specific config.",
            _USER_PLATFORM_CONFIG,
        )
        return ConfigManager._load_section(_DEFAULT_PLATFORM_CONFIG, "platform")
```

### Change 7 — Update module docstring

**Why:** Reflects new design — installer writes flat platform.yaml,
runtime loads it without OS detection.

---

## test_config.py

**Path:** `tests/test_config.py`

### Change 8 — MINIMAL_PLATFORM_YAML is now flat

**Why:** Tests simulate what the installer writes — a flat config for
one OS, not the nested source-of-truth file.

**BEFORE:**
```python
MINIMAL_PLATFORM_YAML = textwrap.dedent("""\
    platform:
      open_command:
        linux: xdg-open
        darwin: open
        windows: startfile
      nxplayer:
        linux: /usr/NX/bin/nxplayer
        ...
""")
```

**AFTER:**
```python
MINIMAL_PLATFORM_YAML = textwrap.dedent("""\
    platform:
      open_command: xdg-open
      nxplayer: /usr/NX/bin/nxplayer
      terminal:
        app: xfce4-terminal
        exec_flag: -e
""")
```

### Change 9 — Remove os_platform parameter and sys.platform monkeypatch from make_config

**Why:** No runtime OS detection to mock. make_config is simpler.

### Change 10 — Replace TestPlatformConfigLoading OS resolution tests with flat load tests

**Why:** There is no per-OS resolution at runtime anymore. Tests now
cover: flat values loaded correctly, user override applied, missing
user file falls back to default, malformed file raises.

### Change 11 — USER_PLATFORM_OVERRIDE_YAML is now flat

**Why:** Consistent with the flat design. A user editing their
platform.yaml would write flat values, not nested OS keys.

**BEFORE:**
```python
USER_PLATFORM_OVERRIDE_YAML = textwrap.dedent("""\
    platform:
      nxplayer:
        linux: /usr/local/bin/nxplayer
        darwin: /usr/local/bin/nxplayer
        windows: C:\\custom\\nxplayer.exe
""")
```

**AFTER:**
```python
USER_PLATFORM_OVERRIDE_YAML = textwrap.dedent("""\
    platform:
      nxplayer: /usr/local/bin/nxplayer
""")
```
