# exceptions.py

**Path:** python/dbkit/dbkit/exceptions.py
**Syntax:** python
**Generated:** 2026-04-13 13:55:31

```python
"""
dbkit.exceptions - Exception hierarchy for dbkit.

All dbkit exceptions inherit from DBKitError, allowing callers to catch
broadly or narrowly as needed.

Calling code may also raise these exceptions for DB-related domain errors,
e.g. SlugNotFoundError when a resolver lookup returns nothing.

Usage:
    from dbkit.exceptions import DBKitError, SlugNotFoundError

    try:
        project_id = resolver.get_id("projects", "slug", "my-project")
    except SlugNotFoundError as e:
        print(f"Project not found: {e}")
"""


class DBKitError(Exception):
    """Base exception for all dbkit errors."""


class DBConnectionError(DBKitError):
    """
    Raised when a database connection cannot be established or is lost.

    Wraps backend-specific errors (e.g. psycopg.OperationalError) so
    callers do not need to import psycopg directly.
    """


class QueryError(DBKitError):
    """
    Raised when a query fails to execute.

    Wraps backend-specific errors (e.g. psycopg.ProgrammingError) so
    callers do not need to import psycopg directly.
    """


class ConfigError(DBKitError):
    """
    Raised when dbkit configuration is missing or invalid.

    Examples: config file not found, required key absent, invalid value.
    """


class SlugNotFoundError(DBKitError):
    """
    Raised when a SlugResolver lookup finds no matching row.

    Callers may raise this themselves when a resolver returns None and
    the absence is an error condition rather than an expected case.
    """
    
```
