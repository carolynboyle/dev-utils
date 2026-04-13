# test_dbkit_connection.py

**Path:** python/dbkit/tests/test_dbkit_connection.py
**Syntax:** python
**Generated:** 2026-04-13 14:09:28

```python
#!/usr/bin/env python3
"""Quick test of dbkit connection to steward database."""

from dbkit.connection import _load_config
from dbkit import DBConnection

# Test config loading
try:
    config = _load_config()
    print(f"✓ Config loaded: {config}")
except Exception as e:
    print(f"✗ Config failed: {e}")
    exit(1)

# Test connection
try:
    with DBConnection() as db:
        result = db.fetch_scalar("SELECT COUNT(*) FROM projects")
        print(f"✓ Connected to steward! Projects table has {result} rows")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    exit(1)

print("\n✓ All tests passed!")

```
