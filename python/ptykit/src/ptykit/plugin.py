"""
ptykit/plugin.py

PtyKitPlugin base class and PluginRegistry.

Plugins inherit from PtyKitPlugin and override the hooks they need.
The registry loads and manages all active plugins for a session.

Plugin discovery uses Python entry points under the group
'ptykit.plugins'. Any installed package that registers under this
group is discoverable. The config file selects which ones to activate.

Usage:
    # Define a plugin:
    from ptykit.plugin import PtyKitPlugin

    class MapPlugin(PtyKitPlugin):
        name = "map_plugin"

        def on_start(self, context):
            context.state[self.name] = {}

        def on_output(self, line, context):
            if "You are" in line:
                context.state[self.name].setdefault("rooms", []).append(line)

        def on_command(self, command, context):
            rooms = context.state[self.name].get("rooms", [])
            context.write("\\n".join(rooms))

    # Load plugins via registry:
    from ptykit.plugin import PluginRegistry
    registry = PluginRegistry(["ptykit_ccc.map_plugin:MapPlugin"])
    registry.on_start(context)
"""

import importlib
import logging

from ptykit.context import PtyKitContext
from ptykit.exceptions import PtyKitPluginError

log = logging.getLogger("ptykit")


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class PtyKitPlugin:
    """
    Base class for all ptykit plugins.

    Plugins override the hooks they need. All hooks are optional —
    the default implementation does nothing.

    Class attribute:
        name: Unique string identifier for this plugin. Used as the
              key in context.state. Must be set by subclasses.
    """

    name: str = ""

    def on_start(self, context: PtyKitContext) -> None:
        """
        Called once when the PTY wrapper starts, before the program runs.

        Use to initialise per-plugin state:
            context.state[self.name] = {}

        Args:
            context: The shared runtime context.
        """

    def on_exit(self, context: PtyKitContext) -> None:
        """
        Called once when the wrapped program exits.

        Use to flush state, write summaries, or clean up resources.

        Args:
            context: The shared runtime context.
        """

    def on_output(self, line: str, context: PtyKitContext) -> None:
        """
        Called for every line of stdout from the wrapped program.

        Passive observation only — output always reaches the terminal
        regardless of what this hook does. Use to detect room
        transitions, track state, or log output.

        Args:
            line:    A single line of stdout (newline stripped).
            context: The shared runtime context.
        """

    def on_command(self, command: str, context: PtyKitContext) -> None:
        """
        Called when the player types an intercepted command.

        The command is NOT passed to the wrapped program. This hook
        is responsible for the full response. Use context.write() to
        display output and context.send() to inject input if needed.

        Args:
            command: The intercepted command string (lowercase, stripped).
            context: The shared runtime context.
        """


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class PluginRegistry:
    """
    Loads, holds, and dispatches to all active plugins for a session.

    Plugins are specified as dotted paths in the form:
        module.submodule:ClassName

    Example:
        registry = PluginRegistry(["ptykit_ccc.map_plugin:MapPlugin"])
        registry.on_start(context)
        registry.on_output("You are in a cave.", context)
        registry.on_command("map", context)
        registry.on_exit(context)
    """

    def __init__(self, plugin_paths: list[str]) -> None:
        """
        Load and instantiate all plugins from their dotted paths.

        Args:
            plugin_paths: List of dotted plugin paths in the form
                          'module.submodule:ClassName'.

        Raises:
            PtyKitPluginError: If any plugin cannot be imported or
                               instantiated.
        """
        self._plugins: list[PtyKitPlugin] = []
        for path in plugin_paths:
            self._plugins.append(self._load(path))
        log.debug("Loaded %d plugin(s): %s", len(self._plugins),
                  [p.name for p in self._plugins])

    def _load(self, path: str) -> PtyKitPlugin:
        """
        Import and instantiate a plugin from a dotted path.

        Args:
            path: Dotted path in the form 'module.submodule:ClassName'.

        Returns:
            An instantiated PtyKitPlugin subclass.

        Raises:
            PtyKitPluginError: If the module cannot be imported, the
                               class is not found, or it is not a
                               PtyKitPlugin subclass.
        """
        if ":" not in path:
            raise PtyKitPluginError(
                f"Invalid plugin path {path!r}. "
                f"Expected 'module.submodule:ClassName'."
            )

        module_path, class_name = path.rsplit(":", 1)

        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise PtyKitPluginError(
                f"Could not import plugin module {module_path!r}: {exc}"
            ) from exc

        cls = getattr(module, class_name, None)
        if cls is None:
            raise PtyKitPluginError(
                f"Class {class_name!r} not found in module {module_path!r}"
            )

        if not (isinstance(cls, type) and issubclass(cls, PtyKitPlugin)):
            raise PtyKitPluginError(
                f"{class_name!r} in {module_path!r} is not a "
                f"PtyKitPlugin subclass"
            )

        if not cls.name:
            raise PtyKitPluginError(
                f"{class_name!r} must set a non-empty class attribute 'name'"
            )

        return cls()

    # -- Dispatch hooks -------------------------------------------------------

    def on_start(self, context: PtyKitContext) -> None:
        """Call on_start on all registered plugins."""
        for plugin in self._plugins:
            plugin.on_start(context)

    def on_exit(self, context: PtyKitContext) -> None:
        """Call on_exit on all registered plugins."""
        for plugin in self._plugins:
            plugin.on_exit(context)

    def on_output(self, line: str, context: PtyKitContext) -> None:
        """Call on_output on all registered plugins."""
        for plugin in self._plugins:
            plugin.on_output(line, context)

    def on_command(self, command: str, context: PtyKitContext) -> None:
        """Call on_command on all registered plugins."""
        for plugin in self._plugins:
            plugin.on_command(command, context)

    @property
    def plugins(self) -> list[PtyKitPlugin]:
        """Return the list of loaded plugin instances."""
        return list(self._plugins)
