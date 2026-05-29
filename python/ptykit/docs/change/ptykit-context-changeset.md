# ptykit — context.py Changeset

**File:** `src/ptykit/context.py`
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
ptykit/context.py

PtyKitContext — the object passed to every plugin method.

Gives plugins access to session state, per-plugin storage, and the
ability to write to the terminal or send input to the wrapped program.

No plugin should import from wrapper.py directly. All interaction with
the PTY happens through the context object.

Usage:
    # In a plugin:
    def on_command(self, command: str, context: PtyKitContext) -> None:
        context.write("Hello from plugin!")
        my_state = context.state[self.name]
"""

from datetime import datetime
from typing import Callable


class PtyKitContext:
    """
    Runtime context passed to every plugin hook.

    Attributes:
        session_start: Datetime when the wrapper started.
        program:       Name of the wrapped CLI program.
        state:         Per-plugin storage dict, keyed by plugin name.
                       Each plugin gets its own isolated namespace.

    Methods:
        write(text): Write text to the terminal (visible to the user).
        send(text):  Send text to the wrapped program's stdin.
    """

    def __init__(
        self,
        program: str,
        write_fn: Callable[[str], None],
        send_fn: Callable[[str], None],
    ) -> None:
        """
        Initialise the context.

        Args:
            program:  Name of the wrapped CLI program (e.g. 'advent').
            write_fn: Callable that writes text to the terminal.
                      Supplied by PTYWrapper at startup.
            send_fn:  Callable that sends text to the program's stdin.
                      Supplied by PTYWrapper at startup.
        """
        self.session_start: datetime = datetime.now()
        self.program: str = program
        self.state: dict = {}
        self._write_fn = write_fn
        self._send_fn = send_fn

    def write(self, text: str) -> None:
        """
        Write text to the terminal.

        Used by plugins to display output (e.g. the map) to the user.
        Does not send anything to the wrapped program.

        Args:
            text: Text to display. Newline not added automatically.
        """
        self._write_fn(text)

    def send(self, text: str) -> None:
        """
        Send text to the wrapped program's stdin.

        Used by plugins that need to inject input into the program
        (e.g. smol-cave sending a command on behalf of the LLM).

        Args:
            text: Text to send. Include newline if the program expects it.
        """
        self._send_fn(text)
```

---

## Why

**Callable parameters for `write` and `send`** — the context doesn't
own the PTY. The wrapper owns it and passes in the two callables at
construction time. Plugins never touch the PTY directly. This keeps
the context testable without a real PTY — tests just pass in a
`lambda` or a list-appending stub.

**`state: dict` keyed by plugin name** — each plugin initialises its
own namespace in `on_start` with `context.state[self.name] = {}`.
No plugin can stomp another's state. No shared mutable globals.

**`session_start` set at `__init__`** — plugins use this to compute
elapsed time or format timestamps relative to session start.

**No `__slots__`** — keeps it simple and flexible for now. Can be
added later if performance becomes a concern.

---

## Tests

**File:** `tests/test_context.py`

```python
"""
tests/test_context.py

Tests for ptykit.context.PtyKitContext.
"""

from datetime import datetime
from ptykit.context import PtyKitContext


def make_context():
    """Helper: create a context with stub write/send functions."""
    written = []
    sent = []
    ctx = PtyKitContext(
        program="advent",
        write_fn=lambda text: written.append(text),
        send_fn=lambda text: sent.append(text),
    )
    return ctx, written, sent


def test_program_set_correctly():
    ctx, _, _ = make_context()
    assert ctx.program == "advent"


def test_session_start_is_datetime():
    ctx, _, _ = make_context()
    assert isinstance(ctx.session_start, datetime)


def test_state_starts_empty():
    ctx, _, _ = make_context()
    assert ctx.state == {}


def test_write_calls_write_fn():
    ctx, written, _ = make_context()
    ctx.write("Hello!")
    assert written == ["Hello!"]


def test_send_calls_send_fn():
    ctx, _, sent = make_context()
    ctx.send("north\n")
    assert sent == ["north\n"]


def test_state_is_isolated_per_plugin():
    ctx, _, _ = make_context()
    ctx.state["plugin_a"] = {"visits": []}
    ctx.state["plugin_b"] = {"count": 0}
    ctx.state["plugin_a"]["visits"].append("room1")
    assert ctx.state["plugin_b"]["count"] == 0
    assert ctx.state["plugin_a"]["visits"] == ["room1"]


def test_multiple_writes():
    ctx, written, _ = make_context()
    ctx.write("line one\n")
    ctx.write("line two\n")
    assert written == ["line one\n", "line two\n"]
```

---

## Checklist

- [ ] `src/ptykit/context.py` written
- [ ] `tests/test_context.py` written
- [ ] `pytest tests/test_context.py` passes
- [ ] `pytest tests/` passes (all tests still green)
- [ ] `pylint src/ptykit/context.py` passes clean
