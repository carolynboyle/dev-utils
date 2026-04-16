# __init__.py

**Path:** python/dbkit/dbkit/__init__.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
dbkit - Database utility library for dev-utils / Project Crew.

Provides synchronous and asynchronous PostgreSQL connection management,
generic lookup table resolution, and a shared exception hierarchy.

Passwords are never stored here — handled by ~/.pgpass.
Connection config lives in ~/.config/dev-utils/config.yaml under 'dbkit:'.

Quick start:
    from dbkit import DBConnection, SlugResolver

    with DBConnection() as db:
        resolver = SlugResolver(db)
        status_id = resolver.require_id("task_status", "name", "open")
        tasks = db.fetch_all(
            "SELECT * FROM v_tasks WHERE project_slug = %s",
            ("project-crew-db",)
        )

Async quick start:
    from dbkit import AsyncDBConnection, SlugResolver

    async with AsyncDBConnection() as db:
        rows = await db.fetch_all("SELECT * FROM v_projects")
"""

from dbkit.connection import DBConnection, AsyncDBConnection
from dbkit.resolver import SlugResolver
from dbkit.exceptions import (
    DBKitError,
    DBConnectionError,
    QueryError,
    ConfigError,
    SlugNotFoundError,
)

__all__ = [
    # Connection
    "DBConnection",
    "AsyncDBConnection",
    # Resolver
    "SlugResolver",
    # Exceptions
    "DBKitError",
    "DBConnectionError",
    "QueryError",
    "ConfigError",
    "SlugNotFoundError",
]

__version__ = "0.1.0"

```
