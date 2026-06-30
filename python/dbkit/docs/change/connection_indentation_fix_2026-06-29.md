# connection.py — Indentation Fix

**Date:** 2026-06-29
**File:** `dbkit/connection.py`
**Type:** Syntax repair only — no logic, behavior, or encoding-fix changes included.

## Issue

Two methods had body content indented at the same level as their `def` line
instead of one level deeper, making the file invalid Python (would raise
`IndentationError` on import, before ever reaching the `client_encoding`
logic you added).

---

## Change 1 — `DBConnection.__enter__`

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
            client_encoding="utf-8",
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

**Why:** The `try`/`except`/`return self` block must be nested inside the
method body (one indent level deeper than `def`). As pasted, it sat at the
same level as `def __enter__`, which is a syntax error in Python.

---

## Change 2 — `AsyncDBConnection.__aenter__`

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
            client_encoding="utf-8",
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

**Why:** Same issue as Change 1, in the async counterpart.

---

## Verification

Ran `python3 -m py_compile connection.py` — file now compiles without error.

## Note on the `client_encoding` fix itself

Your `client_encoding="utf-8"` addition on both `psycopg.connect()` and
`psycopg.AsyncConnection.connect()` calls was already correct and untouched
by this fix — that's the right place to put it, and it's consistent across
both the sync and async paths. No changes needed there.
