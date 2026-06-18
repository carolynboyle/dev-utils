# nmkit — session_dir config and persistent .nxs file fix

## Summary

nxplayer will not read .nxs files from `/tmp/`. Session files must live
in the NoMachine session directory (`~/Documents/NoMachine/` by default).
This change adds `session_dir` as a configurable YAML key and rewrites
the file-writing logic in `launcher.py` to write persistent, named files
to that directory. The temp file cleanup logic is removed entirely.

---

## nmkit.yaml

**Path:** `src/nmkit/data/nmkit.yaml` AND `~/.config/nmkit/nmkit.yaml`

### Change 1 — Add session_dir key

**Why:** nxplayer requires .nxs files to be in the NoMachine session
directory. The path must be configurable rather than hardcoded.

**BEFORE:**
```yaml
nmkit:
  nxplayer: /usr/NX/bin/nxplayer

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
  nxplayer: /usr/NX/bin/nxplayer
  session_dir: ~/Documents/NoMachine

  terminal:
    app: xfce4-terminal
    exec_flag: -e

  ui:
    title: NX Launcher

  log_level: normal
```

### Change 2 — Update comment block

**Why:** Comment block referenced the old `nxclient` key and did not
document `session_dir`. Updated to reflect current keys.

---

## launcher.py

**Path:** `src/nmkit/launcher.py`

### Change 3 — Read session_dir from config in __init__

**Why:** The session directory must come from config, not be hardcoded.
Tilde is expanded at init time so all path operations use an absolute path.

**BEFORE:**
```python
    def __init__(self, config):
        """
        Initialise Launcher.

        Args:
            config: A ConfigManager instance. Used to read the nxplayer
                    binary path from config.app['nxplayer'].
        """
        self._nxplayer = config.app.get("nxplayer", "/usr/NX/bin/nxplayer")
```

**AFTER:**
```python
    def __init__(self, config):
        """
        Initialise Launcher.

        Args:
            config: A ConfigManager instance. Used to read the nxplayer
                    binary path from config.app['nxplayer'] and the
                    session directory from config.app['session_dir'].
        """
        self._nxplayer    = config.app.get("nxplayer", "/usr/NX/bin/nxplayer")
        session_dir_raw   = config.app.get("session_dir", "~/Documents/NoMachine")
        self._session_dir = Path(session_dir_raw).expanduser()
```

### Change 4 — Replace _write_temp_nxs with _write_nxs

**Why:** The old method wrote to `/tmp/` via `tempfile.NamedTemporaryFile`.
nxplayer cannot read files from that location. The new method writes a
persistent, named file to the configured session directory. One file per
connection (`nmkit-{name}.nxs`), overwritten on each connect.

**BEFORE:**
```python
    @staticmethod
    def _write_temp_nxs(content: str) -> Path:
        """
        Write .nxs content to a temporary file and return its path.

        The file is created in the system temp directory with a .nxs
        suffix and is not auto-deleted (caller is responsible for cleanup).

        Args:
            content: The .nxs XML string to write.

        Returns:
            Path to the written temp file.

        Raises:
            NmkitLaunchError: If the temp file cannot be written.
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".nxs",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                return Path(tmp.name)
        except OSError as exc:
            raise NmkitLaunchError(
                f"Could not write temporary .nxs file: {exc}"
            ) from exc
```

**AFTER:**
```python
    def _write_nxs(self, content: str, name: str) -> Path:
        """
        Write .nxs content to the NoMachine session directory.

        The file is named nmkit-{name}.nxs and written to the session
        directory configured in nmkit.yaml. nxplayer requires session
        files to be in this directory and will not read them from any
        other location. The file persists after launch and is overwritten
        on each connect.

        Args:
            content: The .nxs XML string to write.
            name:    Connection name, used to construct the filename.

        Returns:
            Path to the written .nxs file.

        Raises:
            NmkitLaunchError: If the file cannot be written.
        """
        safe_name = name.replace(" ", "_").replace("/", "_")
        nxs_path  = self._session_dir / f"nmkit-{safe_name}.nxs"

        try:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            nxs_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise NmkitLaunchError(
                f"Could not write .nxs file {nxs_path}: {exc}"
            ) from exc

        log.debug("Wrote session file: %s", nxs_path)
        return nxs_path
```

### Change 5 — Update launch() to use _write_nxs, drop cleanup

**Why:** `_write_nxs` takes the connection name as a second argument.
The `finally` cleanup block is removed — session files are persistent
by design, matching how NoMachine manages its own session files.

**BEFORE:**
```python
    def launch(self, connection: dict) -> None:
        """..."""
        nxs_content = self._render_nxs(connection)
        nxs_path    = self._write_temp_nxs(nxs_content)

        try:
            self._start_nxplayer(nxs_path)
        finally:
            # Always clean up the temp file, even if launch fails.
            try:
                nxs_path.unlink()
            except OSError as exc:
                log.warning("Could not remove temp .nxs file %s: %s", nxs_path, exc)
```

**AFTER:**
```python
    def launch(self, connection: dict) -> None:
        """..."""
        nxs_content = self._render_nxs(connection)
        nxs_path    = self._write_nxs(nxs_content, connection["name"])
        self._start_nxplayer(nxs_path)
```

### Change 6 — Remove tempfile import

**Why:** `tempfile` is no longer used.

**BEFORE:**
```python
import logging
import subprocess
import tempfile
from pathlib import Path
from string import Template
```

**AFTER:**
```python
import logging
import subprocess
from pathlib import Path
from string import Template
```

### Change 7 — Update module and class docstrings

**Why:** Docstrings referenced temp files and `/tmp/`. Updated to
describe the persistent session file approach.

---

## test_launcher.py

**Path:** `tests/test_launcher.py`

### Change 8 — Rewrite for new API

**Why:** `_write_temp_nxs` is gone; `_write_nxs` takes a name argument
and writes to the session directory. `_start_nxclient` is gone;
`_start_nxplayer` is the current method name. Cleanup assertions are
replaced with persistence assertions. New tests added for: filename
sanitisation (spaces → underscores), overwrite behaviour, session dir
creation, tilde expansion, and session_dir from config.

Full test class breakdown:

- `TestRenderNxs` — unchanged in scope; verifies host/port/user
  substitution and XML preamble
- `TestWriteNxs` — replaces `TestWriteTempNxs`; asserts file lands in
  session dir, uses `nmkit-{name}.nxs` naming, persists, overwrites,
  creates missing dirs, raises on write failure
- `TestStartNxplayer` — replaces `TestStartNxclient`; asserts `--config`
  flag, `nxplayer not found` error message, custom binary path, and
  `start_new_session=True`
- `TestLaunch` — replaces `TestLaunch`; asserts end-to-end file write +
  launch, file persistence, write failure propagation, nxplayer-not-found
  propagation, session_dir from config, tilde expansion

---

## install.sh

**Path:** `install.sh`

### Change 9 — Rename check_nxclient to check_nxplayer

**Why:** The function checked for `nxclient`, which is the wrong binary.
NoMachine installs `nxplayer`. Function name, binary name, path, and
warning messages updated throughout.

**BEFORE:**
```bash
check_nxclient() {
    if command -v nxclient &>/dev/null || [[ -x "/usr/NX/bin/nxclient" ]]; then
        ok "NoMachine nxclient found."
        return
    fi

    warn "NoMachine nxclient was not found at /usr/NX/bin/nxclient."
    warn "nmkit requires NoMachine to be installed on this machine."
    warn "Download it from: https://www.nomachine.com/download"
    warn ""
    warn "If nxclient is installed in a non-standard location, update"
    warn "the 'nxclient' path in ~/.config/nmkit/nmkit.yaml after install."
}
```

**AFTER:**
```bash
check_nxplayer() {
    if command -v nxplayer &>/dev/null || [[ -x "/usr/NX/bin/nxplayer" ]]; then
        ok "NoMachine nxplayer found."
        return
    fi

    warn "NoMachine nxplayer was not found at /usr/NX/bin/nxplayer."
    warn "nmkit requires NoMachine to be installed on this machine."
    warn "Download it from: https://www.nomachine.com/download"
}
```

### Change 10 — Update main() call site

**Why:** `check_nxclient` renamed to `check_nxplayer`.

**BEFORE:**
```bash
    find_python
    check_nxclient
    choose_install_dir
```

**AFTER:**
```bash
    find_python
    check_nxplayer
    choose_install_dir
```

### Change 11 — Remove nxclient reference from print_next_steps

**Why:** The next-steps block told users to edit `nmkit.yaml` if
`nxclient` was in a non-standard location. That hint is removed — users
who need to override paths don't need the installer to explain it.
