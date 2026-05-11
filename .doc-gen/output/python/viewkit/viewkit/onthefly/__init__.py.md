# __init__.py

**Path:** python/viewkit/viewkit/onthefly/__init__.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
viewkit.onthefly - On-the-fly query tool for viewkit.

A command-line utility for running ad-hoc SQL queries against
PostgreSQL databases using viewkit's YAML query registry and
dbkit's connection management.

Public API:
    OTFConfig        — loads OTF configuration from dev-utils config.yaml
    OTFError         — base exception
    OTFConfigError   — config file missing, unreadable, or malformed
    OTFQueryError    — query file or definition invalid
    OTFRunError      — execution failure (connection, query, output)
"""

from viewkit.onthefly.config import OTFConfig
from viewkit.onthefly.exceptions import (
    OTFError,
    OTFConfigError,
    OTFQueryError,
    OTFRunError,
)

__all__ = [
    "OTFConfig",
    "OTFError",
    "OTFConfigError",
    "OTFQueryError",
    "OTFRunError",
]

```
