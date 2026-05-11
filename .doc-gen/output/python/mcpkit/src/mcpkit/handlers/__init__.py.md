# __init__.py

**Path:** python/mcpkit/src/mcpkit/handlers/__init__.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
mcpkit.handlers - Built-in and model handlers for mcpkit.

Handlers are Python functions that perform work within a workflow step.
They're discovered and registered by the ToolRegistry.
"""

from mcpkit.handlers.builtins import (
    read_file,
    write_file,
    read_yaml,
    read_json,
    write_json,
    fetch_url,
    list_files,
    file_exists,
)
from mcpkit.handlers.models import call_ollama, list_ollama_models

__all__ = [
    "read_file",
    "write_file",
    "read_yaml",
    "read_json",
    "write_json",
    "fetch_url",
    "list_files",
    "file_exists",
    "call_ollama",
    "list_ollama_models",
]
```
