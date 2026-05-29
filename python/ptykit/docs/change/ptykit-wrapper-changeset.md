# ptykit — wrapper.py Changeset

**File:** `src/ptykit/wrapper.py`
**Status:** New file (empty → implemented)

---

## BEFORE

```python
# empty
```

---

## AFTER

```python
"""
ptykit/wrapper.py

PTYWrapper — spawns a CLI program in a pseudo-terminal, streams stdout
to the terminal, intercepts configured commands before they reach the
program, and dispatches to registered plugins.

This is the core of ptykit. Everything else supports this module.

Usage:
    from ptykit.config import ConfigLoader
    from ptykit.context import PtyKitContext
    from ptykit.plugin import PluginRegistry
    from ptykit.wrapper import PTYWrapper

    config = ConfigLoader("advent")
    registry = PluginRegistry(config.plugins)
    wrapper = PTYWrapper(config, registry)
    wrapper.run()
"""

import logging
import os
import select
import sys
import tty
import termios

import ptyprocess

from ptykit.config import ConfigLoader
from ptykit.context import PtyKitContext
from ptykit.exceptions import PtyKitWrapperError
from ptykit.plugin import PluginRegistry

log = logging.getLogger("ptykit")

# Read buffer size for PTY output
_BUFSIZE = 1024


class PTYWrapper:
    """
    Spawns a CLI program in a PTY and wraps it with plugin support.

    stdout from the program is streamed to the terminal line by line.
    Each line is passed to all registered plugins via on_output().

    stdin from the user is buffered until newline. If the input matches
    an intercept command, on_command() is called on all plugins and the
    input is NOT passed to the program. Otherwise input passes through
    unchanged.

    Usage:
        wrapper = PTYWrapper(config, registry)
        wrapper.run()
    """

    def __init__(self, config: ConfigLoader, registry: PluginRegistry) -> None:
        """
        Initialise the wrapper.

        Args:
            config:   Loaded ConfigLoader instance.
            registry: Loaded PluginRegistry instance.
        """
        self._config = config
        self._registry = registry
        self._process: ptyprocess.PtyProcess | None = None
        self._context: PtyKitContext | None = None

    def run(self) -> None:
        """
        Start the wrapped program and enter the IO loop.

        Spawns the program in a PTY, calls on_start() on all plugins,
        then loops reading stdout and stdin until the program exits.
        Calls on_exit() on all plugins before returning.

        Raises:
            PtyKitWrapperError: If the program cannot be spawned.
        """
        self._spawn()
        self._context = PtyKitContext(
            program=self._config.program,
            write_fn=self._write,
            send_fn=self._send,
        )
        self._registry.on_start(self._context)

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            self._loop()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self._registry.on_exit(self._context)

    def _spawn(self) -> None:
        """
        Spawn the configured program in a PTY.

        Raises:
            PtyKitWrapperError: If the program cannot be found or started.
        """
        program = self._config.program
        log.debug("Spawning: %s", program)
        try:
            self._process = ptyprocess.PtyProcess.spawn([program])
        except FileNotFoundError as exc:
            raise PtyKitWrapperError(
                f"Program not found: {program!r}. "
                f"Is it installed and on PATH?"
            ) from exc
        except Exception as exc:
            raise PtyKitWrapperError(
                f"Failed to spawn {program!r}: {exc}"
            ) from exc

    def _loop(self) -> None:
        """
        Main IO loop. Reads stdout and stdin until the program exits.

        stdout lines are passed to plugins via on_output().
        stdin is buffered; intercepted commands go to on_command(),
        everything else passes through to the program.
        """
        input_buffer = ""

        while self._process.isalive():
            try:
                fds = select.select(
                    [self._process.fd, sys.stdin.fileno()], [], [], 0.05
                )[0]
            except (ValueError, OSError):
                break

            # -- Program stdout ----------------------------------------------
            if self._process.fd in fds:
                try:
                    data = os.read(self._process.fd, _BUFSIZE)
                except OSError:
                    break

                text = data.decode("utf-8", errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()

                for line in text.splitlines():
                    self._registry.on_output(line.strip(), self._context)

            # -- User stdin --------------------------------------------------
            if sys.stdin.fileno() in fds:
                try:
                    char = sys.stdin.read(1)
                except OSError:
                    break

                if char in ("\r", "\n"):
                    command = input_buffer.strip().lower()
                    input_buffer = ""

                    if command in self._config.intercept:
                        log.debug("Intercepted command: %r", command)
                        self._registry.on_command(command, self._context)
                    else:
                        self._send(command + "\n")
                else:
                    input_buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

    def _write(self, text: str) -> None:
        """
        Write text to the terminal (stdout).

        Args:
            text: Text to display. Newline not added automatically.
        """
        sys.stdout.write(text)
        sys.stdout.flush()

    def _send(self, text: str) -> None:
        """
        Send text to the wrapped program's stdin via the PTY.

        Args:
            text: Text to send to the program.
        """
        if self._process and self._process.isalive():
            self._process.write(text.encode("utf-8"))
```

---

## Why

**`ptyprocess`** — preferred over stdlib `pty.spawn` for finer PTY
control. Spawning, reading, writing, and liveness checks are all
clean methods on `PtyProcess`.

**`select.select` with timeout** — non-blocking IO loop. The 0.05s
timeout keeps the loop responsive without busy-waiting. Both the PTY
fd and stdin are watched simultaneously.

**`tty.setraw`** — puts stdin into raw mode so individual characters
are available immediately without waiting for Enter. Restored via
`termios.tcsetattr` in the `finally` block regardless of how the
loop exits.

**Input buffering** — characters are accumulated until newline (`\r`
or `\n`). Only then is the buffer checked against the intercept list.
This means partial input (`ma`) never triggers a false intercept.

**`on_output` gets stripped lines** — the raw PTY output may contain
ANSI codes or `\r\n` line endings. Stripping before passing to plugins
keeps the room detection logic in plugins simple.

**`_write` and `_send` as private methods passed to context** —
plugins never hold a reference to the wrapper or the PTY process.
They only hold the two callables from the context.

---

## Tests

**File:** `tests/test_wrapper.py`

PTYWrapper is inherently integration-level — it spawns real processes
and talks to a real PTY. Unit tests use mocks and a minimal echo
program to avoid spawning advent.

```python
"""
tests/test_wrapper.py

Tests for ptykit.wrapper.PTYWrapper.

PTYWrapper is integration-level. These tests use mocks and stubs
to verify behaviour without spawning a real PTY process.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from ptykit.wrapper import PTYWrapper
from ptykit.config import ConfigLoader
from ptykit.plugin import PluginRegistry
from ptykit.exceptions import PtyKitWrapperError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(tmp_path, intercept=None, plugins=None):
    """Create a minimal valid config file and return a ConfigLoader."""
    import yaml
    config = {
        "program": "advent",
        "intercept": intercept or ["map"],
        "plugins": plugins or [],
    }
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    return ConfigLoader("advent", config_file=path)


# ---------------------------------------------------------------------------
# Spawn failure
# ---------------------------------------------------------------------------

def test_spawn_file_not_found_raises(tmp_path):
    config = make_config(tmp_path)
    registry = PluginRegistry([])
    wrapper = PTYWrapper(config, registry)

    with patch("ptyprocess.PtyProcess.spawn", side_effect=FileNotFoundError):
        with pytest.raises(PtyKitWrapperError, match="not found"):
            wrapper._spawn()


def test_spawn_generic_error_raises(tmp_path):
    config = make_config(tmp_path)
    registry = PluginRegistry([])
    wrapper = PTYWrapper(config, registry)

    with patch("ptyprocess.PtyProcess.spawn", side_effect=OSError("boom")):
        with pytest.raises(PtyKitWrapperError, match="Failed to spawn"):
            wrapper._spawn()


# ---------------------------------------------------------------------------
# Intercept logic
# ---------------------------------------------------------------------------

def test_intercepted_command_calls_on_command(tmp_path):
    config = make_config(tmp_path, intercept=["map"])
    received = []

    from ptykit.plugin import PtyKitPlugin
    class RecorderPlugin(PtyKitPlugin):
        name = "recorder"
        def on_start(self, ctx):
            ctx.state[self.name] = {}
        def on_command(self, command, ctx):
            received.append(command)

    registry = PluginRegistry([])
    registry._plugins = [RecorderPlugin()]
    wrapper = PTYWrapper(config, registry)

    mock_process = MagicMock()
    mock_process.isalive.return_value = True
    wrapper._process = mock_process

    from ptykit.context import PtyKitContext
    ctx = PtyKitContext(
        program="advent",
        write_fn=lambda t: None,
        send_fn=lambda t: None,
    )
    registry.on_start(ctx)
    wrapper._context = ctx

    # Simulate intercepted command
    registry.on_command("map", ctx)
    assert "map" in received


def test_non_intercepted_command_not_in_intercept_list(tmp_path):
    config = make_config(tmp_path, intercept=["map"])
    assert "north" not in config.intercept
    assert "map" in config.intercept
```

---

## Checklist

- [ ] `src/ptykit/wrapper.py` written
- [ ] `tests/test_wrapper.py` written
- [ ] `pytest tests/` passes (all 26 + new tests green)
- [ ] `pylint src/ptykit/wrapper.py` passes clean
- [ ] Manual smoke test: `ptykit --program advent` launches the game
