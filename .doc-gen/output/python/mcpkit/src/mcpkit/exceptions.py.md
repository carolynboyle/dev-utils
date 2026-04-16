# exceptions.py

**Path:** python/mcpkit/src/mcpkit/exceptions.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
mcpkit.exceptions - Custom exception hierarchy for mcpkit.

All mcpkit exceptions inherit from MCPKitError, allowing callers to catch
broadly or narrowly as needed.
"""


class MCPKitError(Exception):
    """Base exception for all mcpkit errors."""


class ConfigError(MCPKitError):
    """
    Raised when configuration is missing or invalid.

    Examples: config file not found, required key missing, invalid value.
    """


class ToolNotFoundError(MCPKitError):
    """Raised when a tool referenced in workflow.yaml doesn't exist in tools.yaml."""


class HandlerNotFoundError(MCPKitError):
    """
    Raised when a handler function cannot be found or imported.

    Example: tools.yaml references "handlers.nonexistent_function" but it doesn't exist.
    """


class ValidationError(MCPKitError):
    """Raised when input validation fails (e.g., required field missing)."""


class ExecutionError(MCPKitError):
    """Raised when a handler function fails during execution."""


class WorkflowError(MCPKitError):
    """Raised when workflow execution fails (e.g., step failed, approval denied)."""

```
