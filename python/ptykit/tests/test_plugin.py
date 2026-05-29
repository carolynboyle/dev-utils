"""
tests/test_plugin.py

Tests for ptykit.plugin.PtyKitPlugin and PluginRegistry.
"""

import pytest
from ptykit.plugin import PtyKitPlugin, PluginRegistry
from ptykit.context import PtyKitContext
from ptykit.exceptions import PtyKitPluginError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_context():
    written = []
    sent = []
    ctx = PtyKitContext(
        program="advent",
        write_fn=lambda t: written.append(t),
        send_fn=lambda t: sent.append(t),
    )
    return ctx, written, sent


class GoodPlugin(PtyKitPlugin):
    name = "good_plugin"

    def on_start(self, context):
        context.state[self.name] = {"started": True}

    def on_output(self, line, context):
        context.state[self.name].setdefault("lines", []).append(line)

    def on_command(self, command, context):
        context.write(f"command received: {command}")

    def on_exit(self, context):
        context.state[self.name]["exited"] = True


class NoNamePlugin(PtyKitPlugin):
    pass  # name not set — should fail registry load


# ---------------------------------------------------------------------------
# PtyKitPlugin base class
# ---------------------------------------------------------------------------

def test_base_class_hooks_are_noop():
    """Base class hooks must not raise."""
    ctx, _, _ = make_context()
    plugin = PtyKitPlugin()
    plugin.on_start(ctx)
    plugin.on_output("some line", ctx)
    plugin.on_command("map", ctx)
    plugin.on_exit(ctx)


# ---------------------------------------------------------------------------
# PluginRegistry — loading
# ---------------------------------------------------------------------------

def test_registry_loads_valid_plugin():
    registry = PluginRegistry(["tests.test_plugin:GoodPlugin"])
    assert len(registry.plugins) == 1
    assert registry.plugins[0].name == "good_plugin"


def test_registry_empty_plugin_list():
    registry = PluginRegistry([])
    assert registry.plugins == []


def test_registry_invalid_path_format_raises():
    with pytest.raises(PtyKitPluginError, match="Invalid plugin path"):
        PluginRegistry(["no_colon_here"])


def test_registry_missing_module_raises():
    with pytest.raises(PtyKitPluginError, match="Could not import"):
        PluginRegistry(["ptykit.nonexistent_module:SomeClass"])


def test_registry_missing_class_raises():
    with pytest.raises(PtyKitPluginError, match="not found in module"):
        PluginRegistry(["ptykit.plugin:NonExistentClass"])


def test_registry_non_plugin_class_raises():
    with pytest.raises(PtyKitPluginError, match="not a PtyKitPlugin subclass"):
        PluginRegistry(["ptykit.plugin:PluginRegistry"])


def test_registry_no_name_raises():
    with pytest.raises(PtyKitPluginError, match="must set a non-empty"):
        PluginRegistry(["tests.test_plugin:NoNamePlugin"])


# ---------------------------------------------------------------------------
# PluginRegistry — dispatch
# ---------------------------------------------------------------------------

def test_on_start_initialises_state():
    ctx, _, _ = make_context()
    registry = PluginRegistry(["tests.test_plugin:GoodPlugin"])
    registry.on_start(ctx)
    assert ctx.state["good_plugin"]["started"] is True


def test_on_output_called_with_line():
    ctx, _, _ = make_context()
    registry = PluginRegistry(["tests.test_plugin:GoodPlugin"])
    registry.on_start(ctx)
    registry.on_output("You are in a cave.", ctx)
    assert "You are in a cave." in ctx.state["good_plugin"]["lines"]


def test_on_command_writes_to_terminal():
    ctx, written, _ = make_context()
    registry = PluginRegistry(["tests.test_plugin:GoodPlugin"])
    registry.on_start(ctx)
    registry.on_command("map", ctx)
    assert any("map" in w for w in written)


def test_on_exit_updates_state():
    ctx, _, _ = make_context()
    registry = PluginRegistry(["tests.test_plugin:GoodPlugin"])
    registry.on_start(ctx)
    registry.on_exit(ctx)
    assert ctx.state["good_plugin"]["exited"] is True
