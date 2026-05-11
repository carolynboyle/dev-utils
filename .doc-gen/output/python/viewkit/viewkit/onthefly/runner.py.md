# runner.py

**Path:** python/viewkit/viewkit/onthefly/runner.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
viewkit.onthefly.runner - Query execution for the OTF tool.

Loads a query definition from the entity's YAML file, opens a
synchronous database connection via dbkit, dispatches to the
appropriate fetch method, and returns an OTFResult.

The runner returns raw data only. Formatting is the caller's concern.

Usage:
    from viewkit.onthefly.config import OTFConfig
    from viewkit.onthefly.runner import run_query

    cfg = OTFConfig()
    result = run_query(cfg, "projects", "list_all")
    # result.query_type → "select_all"
    # result.data       → [{"id": 1, "name": "..."}, ...]
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dbkit.connection import DBConnection
from dbkit.exceptions import ConfigError, DBConnectionError, QueryError
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

from viewkit.onthefly.config import OTFConfig
from viewkit.onthefly.exceptions import OTFQueryError, OTFRunError


@dataclass
class OTFResult:
    """
    The result of a single OTF query execution.

    Attributes:
        query_type: One of select_all, select_one, select_scalar, execute.
                    Tells the formatter how to handle data.
        data:       The raw result from dbkit.
                    select_all    → list[dict]
                    select_one    → dict | None
                    select_scalar → single value or None
                    execute       → None
    """
    query_type: str
    data: Any


def run_query(
    cfg: OTFConfig,
    entity: str,
    name: str,
    params: Optional[tuple] = None,
) -> OTFResult:
    """
    Load and execute a named query, returning an OTFResult.

    Args:
        cfg:    OTFConfig instance (caller constructs once, passes through).
        entity: Entity name — maps to a YAML file in queries_dir
                (e.g. "projects" → queries_dir/projects.yaml).
        name:   Query name within the entity (e.g. "list_all").
        params: Optional query parameters as a tuple, matching %s
                placeholders in the SQL. Pass None for parameterless
                queries.

    Returns:
        OTFResult with query_type and data populated.

    Raises:
        OTFQueryError: If the query file or query definition is not found
                       or is malformed.
        OTFRunError:   If the database connection or query execution fails.
    """
    queries_file = _resolve_queries_file(cfg.queries_dir, entity)
    query_def = _load_query(queries_file, entity, name)
    params = params or ()

    try:
        with DBConnection() as db:
            data = _dispatch(db, query_def.query_type, query_def.sql, params)
    except ConfigError as exc:
        raise OTFRunError(
            f"Database configuration error: {exc}"
        ) from exc
    except DBConnectionError as exc:
        raise OTFRunError(
            f"Could not connect to database: {exc}"
        ) from exc
    except QueryError as exc:
        raise OTFRunError(
            f"Query '{entity}.{name}' failed: {exc}"
        ) from exc

    return OTFResult(query_type=query_def.query_type, data=data)


# -- Internal helpers --------------------------------------------------------

def _resolve_queries_file(queries_dir: Path, entity: str) -> Path:
    """
    Resolve the YAML file path for an entity.

    Args:
        queries_dir: Directory containing per-entity query YAML files.
        entity:      Entity name (e.g. "projects").

    Returns:
        Path to the entity's queries YAML file.

    Raises:
        OTFQueryError: If the file does not exist.
    """
    path = queries_dir / f"{entity}.yaml"
    if not path.exists():
        raise OTFQueryError(
            f"No query file found for entity '{entity}': {path}. "
            f"Expected a YAML file at {path}."
        )
    return path


def _load_query(queries_file: Path, entity: str, name: str):
    """
    Load and parse a query definition from a YAML file.

    Args:
        queries_file: Path to the entity's queries YAML file.
        entity:       Entity name.
        name:         Query name within the entity.

    Returns:
        QueryDef for the requested query.

    Raises:
        OTFQueryError: If the file is malformed or the query is not found.
    """
    try:
        builder = QueryBuilder(queries_file)
        loader = QueryLoader(builder)
        return loader.get(entity, name)
    except KeyError as exc:
        raise OTFQueryError(
            f"Query '{entity}.{name}' not found in {queries_file}."
        ) from exc
    except Exception as exc:
        raise OTFQueryError(
            f"Could not load query '{entity}.{name}' from {queries_file}: {exc}"
        ) from exc


def _dispatch(db: DBConnection, query_type: str, sql: str, params: tuple) -> Any:
    """
    Dispatch to the appropriate DBConnection method based on query_type.

    Args:
        db:         Open DBConnection instance.
        query_type: One of select_all, select_one, select_scalar, execute.
        sql:        SQL string to execute.
        params:     Query parameters tuple.

    Returns:
        Result from the appropriate dbkit method.

    Raises:
        OTFRunError: If query_type is not recognised.
    """
    if query_type == "select_all":
        return db.fetch_all(sql, params)
    elif query_type == "select_one":
        return db.fetch_one(sql, params)
    elif query_type == "select_scalar":
        return db.fetch_scalar(sql, params)
    elif query_type == "execute":
        db.execute(sql, params)
        return None
    else:
        raise OTFRunError(
            f"Unknown query_type '{query_type}'. "
            f"Must be one of: select_all, select_one, select_scalar, execute."
        )
```
