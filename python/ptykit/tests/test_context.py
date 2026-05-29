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
