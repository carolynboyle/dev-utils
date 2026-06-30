# Changedoc — dbkit: Fix client_encoding for SQL_ASCII databases

**File:** `python/dbkit/dbkit/connection.py`
**Repo:** `dev-utils`
**Date:** 2026-06-29

---

## Problem

psycopg 3.3.4 changed behavior for `SQL_ASCII` databases. When no
`client_encoding` is specified on connect, psycopg now returns text
columns as `bytes` instead of `str`. This caused all string values
fetched from the wcyj database to come back as byte strings, breaking
every query result in Curator.

psycopg 3.3.3 (used on the original dev machine) decoded automatically.
The regression was introduced in 3.3.4 and affects any database whose
server encoding is `SQL_ASCII`.

The fix was applied locally to the venv at the time but never committed
to the dev-utils repo, leaving the repo out of sync with the installed
version.

---

## Fix

Add `client_encoding="utf-8"` to both the sync and async connect calls.
This tells psycopg to decode text as UTF-8 regardless of the server's
reported encoding, restoring the pre-3.3.4 behavior.

---

## Changes

### `DBConnection.__enter__` (sync)

**BEFORE:**
```python
def __enter__(self) -> "DBConnection":
    try:
        self._conn = psycopg.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**AFTER:**
```python
def __enter__(self) -> "DBConnection":
    try:
        self._conn = psycopg.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
            client_encoding="utf-8",
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

---

### `AsyncDBConnection.__aenter__` (async)

**BEFORE:**
```python
async def __aenter__(self) -> "AsyncDBConnection":
    try:
        self._conn = await psycopg.AsyncConnection.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**AFTER:**
```python
async def __aenter__(self) -> "AsyncDBConnection":
    try:
        self._conn = await psycopg.AsyncConnection.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
            client_encoding="utf-8",
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

---

## Why

`client_encoding="utf-8"` instructs psycopg to decode all text received
from the server as UTF-8, regardless of the database server's reported
encoding (`SQL_ASCII` in this case). This is the correct fix because:

1. The actual data in wcyj is UTF-8 — `SQL_ASCII` is a PostgreSQL
   encoding that means "no encoding enforcement", not "data is ASCII".
2. psycopg 3.3.4's stricter behavior is technically correct per spec,
   but requires an explicit encoding hint when the server reports
   `SQL_ASCII`.
3. The fix belongs in dbkit, not in application code — dbkit is the
   connection layer and should handle this transparently for all callers.

---

## After Applying

Reinstall dbkit in any venv that uses it:
```bash
pip install --force-reinstall -e ~/projects/dev-utils/python/dbkit
```

Commit to dev-utils:
```bash
git add python/dbkit/dbkit/connection.py
git commit -m "patch: fix client_encoding for SQL_ASCII databases (psycopg 3.3.4)"
```
