# setupkit_installer_setup_logger.md

**Path:** python/setupkit/docs/changedocs/setupkit_installer_setup_logger.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# Change: Wire setup_logger() into installer.py main()

**Date:** 2026-04-25
**File:** `python/setupkit/src/setupkit/installer.py`
**Type:** Bug fix

---

## Background

When `logger.py` was extracted from `installer.py`, the `_setup_logging()`
call was removed from `main()` but never replaced with a call to the new
`setup_logger()`. The logger is named correctly throughout the module and
handlers are defined in `logger.py`, but nothing ever calls `setup_logger()`,
so the handlers are never attached. The result is that running setupkit from
the CLI produces no log output and no log file.

---

## Change

### `python/setupkit/src/setupkit/installer.py`

**BEFORE** — top of `main()`, showing the stale comment and missing call:

```python
def main() -> None:
    """
    CLI entry point for setupkit.

    Usage:
        setupkit init    <name>
        setupkit install [<name>] [--force]
        setupkit check   [<name>]
    """
    import argparse
    from setupkit.initialize import init_plugin

   

    parser = argparse.ArgumentParser(
```

**AFTER:**

```python
def main() -> None:
    """
    CLI entry point for setupkit.

    Usage:
        setupkit init    <name>
        setupkit install [<name>] [--force]
        setupkit check   [<name>]
    """
    import argparse
    from setupkit.initialize import init_plugin
    from setupkit.logger import setup_logger

    setup_logger()

    parser = argparse.ArgumentParser(
```

Also remove the stale comment block that preceded the CLI entry point section.

**BEFORE** — stale comment left over from the logger extraction:

```python
# ---------------------------------------------------------------------------
# Logging setup -- _setup_logging function has been replaced by module logger.py
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
```

**AFTER** — single clean section header:

```python
# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
```

---

## Why

`setup_logger()` must be called once at the CLI entry point to attach
handlers to the `setupkit` logger. Without it, `logging.getLogger("setupkit")`
returns a logger with no handlers and all log output is silently discarded.

The import is placed inside `main()` (alongside the existing `argparse` and
`init_plugin` imports) to keep module-level imports clean and consistent with
the existing pattern in that function. `setup_logger()` must not be called at
module import time — only when the CLI is actually invoked.

---

## Testing

After applying this change, verify logging works:

```bash
setupkit check nonexistent-plugin
```

Expected: error message on stderr AND a new entry in
`~/.local/share/dev-utils/setupkit.log`.

```bash
cat ~/.local/share/dev-utils/setupkit.log
```

Should show a timestamped ERROR entry for the failed check.

```
