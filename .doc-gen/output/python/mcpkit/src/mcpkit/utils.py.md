# utils.py

**Path:** python/mcpkit/src/mcpkit/utils.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
mcpkit.utils - Utility functions for mcpkit.

Variable interpolation, path expansion, and common operations used across
the framework.
"""

import re
from pathlib import Path
from typing import Any, Dict


def interpolate(text: str, variables: Dict[str, Any]) -> str:
    """
    Interpolate variables in text using {{ var_name }} syntax.

    Supports nested access: {{ obj.key }} (limited — only one level).

    Args:
        text: String containing {{ var_name }} placeholders
        variables: Dict of variable names to values

    Returns:
        Text with all {{ var_name }} replaced by their values

    Example:
        >>> interpolate("Hello {{ name }}", {"name": "Alice"})
        "Hello Alice"
    """

    def replace_var(match):
        var_name = match.group(1).strip()
        if var_name in variables:
            return str(variables[var_name])
        # If variable not found, leave it as-is (don't error)
        return match.group(0)

    pattern = r"\{\{\s*([^}]+)\s*\}\}"
    return re.sub(pattern, replace_var, text)


def expand_path(path_str: str) -> Path:
    """
    Expand a path string, handling ~ and environment variables.

    Args:
        path_str: Path string (e.g., "~/projects/foo", "$HOME/bar")

    Returns:
        Expanded Path object

    Example:
        >>> expand_path("~/projects/mcpkit")
        PosixPath('/home/user/projects/mcpkit')
    """
    return Path(path_str).expanduser().expandvars()


def ensure_dir(path: Path) -> Path:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get value from dict, returning default if missing.

    Safe alternative to dict.get() that works predictably.

    Args:
        d: Dictionary
        key: Key to look up
        default: Value to return if key missing

    Returns:
        Value or default
    """
    return d.get(key, default)

```
