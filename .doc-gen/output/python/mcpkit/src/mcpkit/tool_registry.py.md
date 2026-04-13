# tool_registry.py

**Path:** python/mcpkit/src/mcpkit/tool_registry.py
**Syntax:** python
**Generated:** 2026-04-13 13:55:31

```python
"""
mcpkit.tool_registry - Tool registration and handler discovery.

Loads tools.yaml and maps handler references (e.g., "builtins.read_yaml")
to actual Python functions. Validates tool schemas.
"""

import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from mcpkit.exceptions import (
    ConfigError,
    HandlerNotFoundError,
    ToolNotFoundError,
    ValidationError,
)
from mcpkit.utils import expand_path


class Tool:
    """Represents a single MCP tool with its schema and handler."""

    def __init__(self, name: str, definition: Dict[str, Any]):
        """
        Initialize a Tool.

        Args:
            name: Tool identifier (e.g., "parse_manifest")
            definition: Tool definition from tools.yaml
        """
        self.name = name
        self.definition = definition
        self.description = definition.get("description", "")
        self.handler_ref = definition.get("handler", "")
        self.input_schema = definition.get("input_schema", {})
        self.output_description = definition.get("output_description", "")
        self.handler_func: Optional[Callable] = None

    def __repr__(self) -> str:
        return f"Tool(name={self.name}, handler={self.handler_ref})"


class ToolRegistry:
    """
    Load and manage MCP tools from tools.yaml.

    Discovers handler functions, validates tool definitions, and provides
    access to tools by name.
    """

    def __init__(self, tools_yaml_path: Path, handler_modules: List[str]):
        """
        Initialize registry and load tools.

        Args:
            tools_yaml_path: Path to tools.yaml
            handler_modules: List of handler module names to search
                           (e.g., ["mcpkit.handlers.builtins", "my_handlers"])

        Raises:
            ConfigError: If tools.yaml not found or invalid
            HandlerNotFoundError: If a tool references a handler that doesn't exist
        """
        self.tools_yaml_path = expand_path(tools_yaml_path)
        self.handler_modules = handler_modules
        self.tools: Dict[str, Tool] = {}
        self._handlers_cache: Dict[str, Callable] = {}

        self._load_tools()
        self._resolve_handlers()

    def _load_tools(self) -> None:
        """
        Load tools from YAML file.

        Raises:
            ConfigError: If file not found or invalid YAML
        """
        if not self.tools_yaml_path.exists():
            raise ConfigError(f"Tools file not found: {self.tools_yaml_path}")

        try:
            content = self.tools_yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if not data or "tools" not in data:
                raise ConfigError(f"No 'tools' section found in {self.tools_yaml_path}")

            tools_data = data["tools"]
            if not isinstance(tools_data, dict):
                raise ConfigError(
                    f"'tools' section must be a dict, got {type(tools_data)}"
                )

            for tool_name, tool_def in tools_data.items():
                self.tools[tool_name] = Tool(tool_name, tool_def)

        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {self.tools_yaml_path}: {e}")
        except OSError as e:
            raise ConfigError(f"Could not read {self.tools_yaml_path}: {e}")

    def _resolve_handlers(self) -> None:
        """
        Resolve handler functions for all tools.

        Searches through handler_modules to find the actual functions
        referenced in tools.yaml.

        Raises:
            HandlerNotFoundError: If a handler cannot be found
        """
        for tool in self.tools.values():
            handler_func = self._find_handler(tool.handler_ref)
            tool.handler_func = handler_func

    def _find_handler(self, handler_ref: str) -> Callable:
        """
        Find a handler function by reference string.

        Supports format: "module.function" (e.g., "builtins.read_yaml")

        Args:
            handler_ref: Handler reference string

        Returns:
            The callable handler function

        Raises:
            HandlerNotFoundError: If handler not found or not callable
        """
        if not handler_ref or not isinstance(handler_ref, str):
            raise HandlerNotFoundError(f"Invalid handler reference: {handler_ref}")

        # Check cache first
        if handler_ref in self._handlers_cache:
            return self._handlers_cache[handler_ref]

        # Parse "module.function" format
        parts = handler_ref.rsplit(".", 1)
        if len(parts) != 2:
            raise HandlerNotFoundError(
                f"Invalid handler reference format: {handler_ref}\n"
                f"Expected: module.function (e.g., 'builtins.read_yaml')"
            )

        module_name, func_name = parts

        # Try to find the handler in registered modules
        for handler_module_name in self.handler_modules:
            try:
                # Try exact match first (e.g., "builtins" → "mcpkit.handlers.builtins")
                if module_name == handler_module_name.split(".")[-1]:
                    module = importlib.import_module(handler_module_name)
                    if hasattr(module, func_name):
                        func = getattr(module, func_name)
                        if callable(func):
                            self._handlers_cache[handler_ref] = func
                            return func
            except ImportError:
                continue

        # If not found, try as absolute module path
        try:
            full_module_path = f"{module_name}"
            module = importlib.import_module(full_module_path)
            if hasattr(module, func_name):
                func = getattr(module, func_name)
                if callable(func):
                    self._handlers_cache[handler_ref] = func
                    return func
        except ImportError:
            pass

        raise HandlerNotFoundError(
            f"Handler not found: {handler_ref}\n"
            f"Searched in: {', '.join(self.handler_modules)}"
        )

    def get_tool(self, tool_name: str) -> Tool:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool object

        Raises:
            ToolNotFoundError: If tool doesn't exist
        """
        if tool_name not in self.tools:
            available = ", ".join(self.tools.keys()) or "none"
            raise ToolNotFoundError(
                f"Tool not found: {tool_name}\n" f"Available tools: {available}"
            )
        return self.tools[tool_name]

    def list_tools(self) -> List[str]:
        """Get list of all available tool names."""
        return list(self.tools.keys())

    def describe_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Get a tool description suitable for showing to the user.

        Args:
            tool_name: Name of the tool

        Returns:
            Dict with description, input schema, output description

        Raises:
            ToolNotFoundError: If tool doesn't exist
        """
        tool = self.get_tool(tool_name)
        return {
            "name": tool.name,
            "description": tool.description,
            "handler": tool.handler_ref,
            "input_schema": tool.input_schema,
            "output_description": tool.output_description,
        }

```
