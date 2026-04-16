# resolver.py

**Path:** python/dbkit/dbkit/resolver.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
dbkit.resolver - Generic lookup table resolver.

Handles forward and reverse lookups against any lookup table without
the caller needing to write boilerplate SELECT queries. Designed for
the normalized schema pattern used in the projects database, where
categorical values live in small lookup tables with integer primary keys.

All queries are parameterized — no string interpolation of user-supplied
values. Table and column names are validated against an allowlist before
being interpolated into SQL (they cannot be parameterized in psycopg).

Usage:
    from dbkit.connection import DBConnection
    from dbkit.resolver import SlugResolver

    with DBConnection() as db:
        resolver = SlugResolver(db)

        # Forward: human-readable value → integer ID
        status_id = resolver.get_id("task_status", "name", "open")

        # Reverse: integer ID → human-readable value
        status_name = resolver.get_value("task_status", "id", status_id, "name")

        # Existence check
        if resolver.exists("projects", "slug", "my-project"):
            ...

        # Raise on missing (instead of returning None)
        status_id = resolver.require_id("task_status", "name", "open")
"""

import re
from typing import Any, Optional

from dbkit.connection import DBConnection
from dbkit.exceptions import QueryError, SlugNotFoundError


# ---------------------------------------------------------------------------
# Identifier validation
# ---------------------------------------------------------------------------

# PostgreSQL identifiers: letters, digits, underscore; must not start with digit.
# This is deliberately restrictive — all real table/column names in the
# projects schema satisfy it. Any value that doesn't is rejected rather
# than sanitized.
_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(name: str, label: str = "identifier") -> str:
    """
    Confirm a table or column name is a safe SQL identifier.

    Args:
        name:  The identifier to validate.
        label: Human-readable label used in the error message.

    Returns:
        The name unchanged if valid.

    Raises:
        ValueError: If the name contains characters that are not allowed
                    in an unquoted PostgreSQL identifier.
    """
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Unsafe SQL {label}: {name!r}. "
            "Only letters, digits, and underscores are allowed; "
            "identifier must not start with a digit."
        )
    return name


# ---------------------------------------------------------------------------
# SlugResolver
# ---------------------------------------------------------------------------

class SlugResolver:
    """
    Generic resolver for lookup table queries.

    Wraps forward (name → id) and reverse (id → name) lookups, existence
    checks, and full-table fetches. All SQL values are parameterized;
    table and column names are validated before interpolation.

    Instantiate with an active DBConnection. The connection lifetime is
    managed by the caller — SlugResolver does not open or close it.

    Example:
        with DBConnection() as db:
            resolver = SlugResolver(db)
            priority_id = resolver.get_id("priority", "name", "high")
    """

    def __init__(self, db: DBConnection):
        """
        Args:
            db: An open DBConnection instance. Must be used inside its
                context manager block.
        """
        self._db = db

    # -- Core lookup methods --------------------------------------------------

    def get_id(
        self,
        table: str,
        lookup_col: str,
        value: Any,
        id_col: str = "id",
    ) -> Optional[int]:
        """
        Return the primary key for a matching row, or None.

        The common case: look up an integer ID by a human-readable value.

            status_id = resolver.get_id("task_status", "name", "open")

        Args:
            table:      Table name.
            lookup_col: Column to match against (e.g. "name", "slug").
            value:      Value to search for.
            id_col:     Primary key column name. Defaults to "id".

        Returns:
            The ID value as an int, or None if no row matched.

        Raises:
            ValueError:  If table, lookup_col, or id_col fail identifier validation.
            QueryError:  If the query fails.
        """
        t  = _validate_identifier(table,      "table name")
        lc = _validate_identifier(lookup_col, "lookup column")
        ic = _validate_identifier(id_col,     "id column")

        sql = f"SELECT {ic} FROM {t} WHERE {lc} = %s LIMIT 1"
        return self._db.fetch_scalar(sql, (value,))

    def get_value(
        self,
        table: str,
        lookup_col: str,
        value: Any,
        return_col: str,
    ) -> Optional[Any]:
        """
        Return a single column value from a matching row, or None.

        The reverse case: look up a human-readable value by its ID, or
        look up any column given any other column.

            status_name = resolver.get_value("task_status", "id", 1, "name")
            display     = resolver.get_value("task_status", "name", "open", "display")

        Args:
            table:      Table name.
            lookup_col: Column to match against.
            value:      Value to search for.
            return_col: Column to return.

        Returns:
            The value of return_col, or None if no row matched.

        Raises:
            ValueError:  If any name fails identifier validation.
            QueryError:  If the query fails.
        """
        t  = _validate_identifier(table,      "table name")
        lc = _validate_identifier(lookup_col, "lookup column")
        rc = _validate_identifier(return_col, "return column")

        sql = f"SELECT {rc} FROM {t} WHERE {lc} = %s LIMIT 1"
        return self._db.fetch_scalar(sql, (value,))

    def get_row(
        self,
        table: str,
        lookup_col: str,
        value: Any,
    ) -> Optional[dict]:
        """
        Return a full row as a dict, or None.

        Useful when you need more than one column from a lookup table.

            row = resolver.get_row("task_status", "name", "open")
            # row == {"id": 1, "name": "open", "display": "[ ]", ...}

        Args:
            table:      Table name.
            lookup_col: Column to match against.
            value:      Value to search for.

        Returns:
            Dict of all columns, or None if no row matched.

        Raises:
            ValueError:  If table or lookup_col fail identifier validation.
            QueryError:  If the query fails.
        """
        t  = _validate_identifier(table,      "table name")
        lc = _validate_identifier(lookup_col, "lookup column")

        sql = f"SELECT * FROM {t} WHERE {lc} = %s LIMIT 1"
        return self._db.fetch_one(sql, (value,))

    def get_all(
        self,
        table: str,
        order_by: str = "sort_order",
    ) -> list[dict]:
        """
        Return all rows from a lookup table, ordered for display.

        Useful for populating menus or validating user input against
        the full set of allowed values.

            statuses = resolver.get_all("task_status")
            # [{"id": 1, "name": "open", ...}, {"id": 2, "name": "in progress", ...}]

        Args:
            table:    Table name.
            order_by: Column to sort by. Defaults to "sort_order".
                      Pass "id" or "name" if sort_order is not present.

        Returns:
            List of dicts, one per row.

        Raises:
            ValueError:  If table or order_by fail identifier validation.
            QueryError:  If the query fails.
        """
        t  = _validate_identifier(table,    "table name")
        ob = _validate_identifier(order_by, "order_by column")

        sql = f"SELECT * FROM {t} ORDER BY {ob}"
        return self._db.fetch_all(sql)

    def exists(
        self,
        table: str,
        lookup_col: str,
        value: Any,
    ) -> bool:
        """
        Return True if any row matches, False otherwise.

        Cheaper than get_id() when you only need to know whether a
        value is present, not what its ID is.

            if not resolver.exists("projects", "slug", "my-project"):
                print("No such project.")

        Args:
            table:      Table name.
            lookup_col: Column to match against.
            value:      Value to search for.

        Returns:
            True if at least one matching row exists.

        Raises:
            ValueError:  If table or lookup_col fail identifier validation.
            QueryError:  If the query fails.
        """
        t  = _validate_identifier(table,      "table name")
        lc = _validate_identifier(lookup_col, "lookup column")

        sql = f"SELECT EXISTS (SELECT 1 FROM {t} WHERE {lc} = %s)"
        return bool(self._db.fetch_scalar(sql, (value,)))

    # -- Strict variants (raise on missing) -----------------------------------

    def require_id(
        self,
        table: str,
        lookup_col: str,
        value: Any,
        id_col: str = "id",
    ) -> int:
        """
        Like get_id(), but raises SlugNotFoundError instead of returning None.

        Use this when the absence of a value is a programming error or
        bad user input, not an expected case.

            status_id = resolver.require_id("task_status", "name", user_input)

        Args:
            table:      Table name.
            lookup_col: Column to match against.
            value:      Value to search for.
            id_col:     Primary key column name. Defaults to "id".

        Returns:
            The ID as an int.

        Raises:
            SlugNotFoundError: If no matching row is found.
            ValueError:        If any name fails identifier validation.
            QueryError:        If the query fails.
        """
        result = self.get_id(table, lookup_col, value, id_col)
        if result is None:
            raise SlugNotFoundError(
                f"No row found in '{table}' where {lookup_col} = {value!r}"
            )
        return result

    def require_value(
        self,
        table: str,
        lookup_col: str,
        value: Any,
        return_col: str,
    ) -> Any:
        """
        Like get_value(), but raises SlugNotFoundError instead of returning None.

        Args:
            table:      Table name.
            lookup_col: Column to match against.
            value:      Value to search for.
            return_col: Column to return.

        Returns:
            The value of return_col.

        Raises:
            SlugNotFoundError: If no matching row is found.
            ValueError:        If any name fails identifier validation.
            QueryError:        If the query fails.
        """
        result = self.get_value(table, lookup_col, value, return_col)
        if result is None:
            raise SlugNotFoundError(
                f"No row found in '{table}' where {lookup_col} = {value!r}"
            )
        return result
```
