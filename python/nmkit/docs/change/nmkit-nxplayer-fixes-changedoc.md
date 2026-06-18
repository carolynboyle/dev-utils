# nmkit — nxplayer binary and Connect button fixes

## Summary

NoMachine installs as `nxplayer` not `nxclient`, and uses `--config`
not `--session`. This changedoc covers all affected files plus the
Connect button card selection fix.

---

## launcher.py

**Path:** `src/nmkit/launcher.py`

### Change 1 — Rename config key and update default binary path

**Why:** NoMachine binary is `nxplayer` at `/usr/NX/bin/nxplayer`.
The config key is renamed from `nxclient` to `nxplayer` for clarity.

**BEFORE:**
```python
    def __init__(self, config):
        """
        Initialise Launcher.

        Args:
            config: A ConfigManager instance. Used to read the nxclient
                    binary path from config.app['nxclient'].
        """
        self._nxclient = config.app.get("nxclient", "/usr/NX/bin/nxclient")
```

**AFTER:**
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

### Change 2 — Update class docstring

**BEFORE:**
```python
class Launcher:  # pylint: disable=too-few-public-methods
    """
    Generates temporary .nxs session files and launches nxclient.

    The nxclient binary path is read from the app config. Each launch
    writes a temporary .nxs file, passes it to nxclient, and removes it
    once nxclient has started (nxclient reads the file at startup and does
    not need it to persist).
    ...
    """
```

**AFTER:**
```python
class Launcher:  # pylint: disable=too-few-public-methods
    """
    Generates temporary .nxs session files and launches nxplayer.

    The nxplayer binary path is read from the app config. Each launch
    writes a temporary .nxs file, passes it to nxplayer, and removes it
    once nxplayer has started (nxplayer reads the file at startup and does
    not need it to persist).
    ...
    """
```

### Change 3 — Update _start_nxclient to use --config flag and nxplayer

**Why:** `nxplayer` uses `--config` not `--session`. All references
to `nxclient` updated to `nxplayer` throughout.

**BEFORE:**
```python
    def _start_nxclient(self, nxs_path: Path) -> None:
        """
        Start nxclient as a detached subprocess with the given .nxs file.

        Args:
            nxs_path: Path to the .nxs session file.

        Raises:
            NmkitLaunchError: If nxclient cannot be found or started.
        """
        cmd = [self._nxclient, "--session", str(nxs_path)]
        log.info("Launching: %s", " ".join(cmd))

        try:
            subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise NmkitLaunchError(
                f"nxclient not found at {self._nxclient!r}. "
                "Check the 'nxclient' path in nmkit.yaml."
            ) from exc
        except OSError as exc:
            raise NmkitLaunchError(
                f"Failed to start nxclient: {exc}"
            ) from exc

        log.info(
            "nxclient started for %s (%s)",
            nxs_path.name,
            self._nxclient,
        )
```

**AFTER:**
```python
    def _start_nxplayer(self, nxs_path: Path) -> None:
        """
        Start nxplayer as a detached subprocess with the given .nxs file.

        Args:
            nxs_path: Path to the .nxs session file.

        Raises:
            NmkitLaunchError: If nxplayer cannot be found or started.
        """
        cmd = [self._nxplayer, "--config", str(nxs_path)]
        log.info("Launching: %s", " ".join(cmd))

        try:
            subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise NmkitLaunchError(
                f"nxplayer not found at {self._nxplayer!r}. "
                "Check the 'nxplayer' path in nmkit.yaml."
            ) from exc
        except OSError as exc:
            raise NmkitLaunchError(
                f"Failed to start nxplayer: {exc}"
            ) from exc

        log.info(
            "nxplayer started for %s (%s)",
            nxs_path.name,
            self._nxplayer,
        )
```

### Change 4 — Update launch() to call _start_nxplayer

**BEFORE:**
```python
        try:
            self._start_nxclient(nxs_path)
        finally:
```

**AFTER:**
```python
        try:
            self._start_nxplayer(nxs_path)
        finally:
```

---

## nmkit.yaml

**Path:** `src/nmkit/data/nmkit.yaml` AND `~/.config/nmkit/nmkit.yaml`

**Why:** Config key renamed from `nxclient` to `nxplayer`, path updated.

**BEFORE:**
```yaml
nmkit:
  nxclient: /usr/NX/bin/nxclient
```

**AFTER:**
```yaml
nmkit:
  nxplayer: /usr/NX/bin/nxplayer
```

---

## ui.py

**Path:** `src/nmkit/ui.py`

### Change 5 — Select card when Connect button is clicked

**Why:** Clicking the Connect button consumed the click event before
it reached the card's mousePressEvent, so Edit/Delete buttons never
enabled after clicking Connect.

**BEFORE:**
```python
    def _on_connect(self) -> None:
        """Handle Connect button click — launch the NoMachine session."""
        name = self._connection.get("name", "unknown")
        log.info("Connect requested for '%s'.", name)
```

**AFTER:**
```python
    def _on_connect(self) -> None:
        """Handle Connect button click — select card and launch session."""
        self._on_select(self)
        name = self._connection.get("name", "unknown")
        log.info("Connect requested for '%s'.", name)
```

---

## test_launcher.py

**Path:** `tests/test_launcher.py`

### Change 6 — Update tests for nxplayer rename

**Why:** All references to `nxclient`, `--session`, and `_start_nxclient`
must be updated to match the renamed method and flag.

**BEFORE:**
```python
    config.app = {"nxclient": "/usr/NX/bin/nxclient"}
```

**AFTER:**
```python
    config.app = {"nxplayer": "/usr/NX/bin/nxplayer"}
```

**BEFORE:**
```python
        assert call_args[0] == "/usr/NX/bin/nxclient"
        assert "--session" in call_args
```

**AFTER:**
```python
        assert call_args[0] == "/usr/NX/bin/nxplayer"
        assert "--config" in call_args
```

**BEFORE:**
```python
            with pytest.raises(NmkitLaunchError, match="nxclient not found"):
```

**AFTER:**
```python
            with pytest.raises(NmkitLaunchError, match="nxplayer not found"):
```

**BEFORE:**
```python
        config.app  = {"nxclient": "/custom/path/nxclient"}
        ...
        assert call_args[0] == "/custom/path/nxclient"
```

**AFTER:**
```python
        config.app  = {"nxplayer": "/custom/path/nxplayer"}
        ...
        assert call_args[0] == "/custom/path/nxplayer"
```

**BEFORE:**
```python
            patch.object(Launcher, "_start_nxclient"),
```

**AFTER:**
```python
            patch.object(Launcher, "_start_nxplayer"),
```
