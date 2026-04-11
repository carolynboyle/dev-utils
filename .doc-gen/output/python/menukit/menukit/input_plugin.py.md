# input_plugin.py

**Path:** python/menukit/menukit/input_plugin.py
**Syntax:** python
**Generated:** 2026-04-06 08:55:14

```python
"""
menukit.input_plugin - Interface contract for input plugins.

Any input source (menus, CLI params, Textual TUI, etc.) must implement
this interface. The engine accepts input from any conforming plugin
without knowing or caring which one is active.

Usage:
    from menukit.input_plugin import InputPlugin

    class MyPlugin(InputPlugin):
        def get_action(self) -> tuple[str, dict]:
            ...
"""

from abc import ABC, abstractmethod


class InputPlugin(ABC):
    """
    Base class for all input plugins.

    An input plugin is responsible for determining what action the user
    wants to perform and what parameters to pass to the engine.
    The engine calls get_action() and dispatches on the result.

    Returns:
        tuple[str, dict]: (action_name, parameters)

        action_name — matches an engine operation, e.g. "create_project"
        parameters  — dict of kwargs the engine operation expects,
                      e.g. {"name": "myproject", "language": "python"}

    Example return values:
        ("create_project", {"name": "myproject", "language": "python"})
        ("launch_project", {"name": "myproject"})
        ("quit", {})
    """

    @abstractmethod
    def get_action(self) -> tuple[str, dict]:
        """Collect and return the user's intended action and parameters."""
        
```
