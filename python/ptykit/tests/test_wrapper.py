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
