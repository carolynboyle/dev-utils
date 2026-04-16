# backup_todo.py

**Path:** python/todo/src/todo/backup_todo.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
#!/usr/bin/env python3
"""
todo.backup_todo - Backup current TODO.md to docs/todo.bk/.

Creates a timestamped copy of the TODO.md file. Backup directory
is always a subdirectory of wherever TODO.md lives.

Standalone usage:
    backup-todo

Plugin usage: invoked by projs tools menu via entry point.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


_DEFAULT_TODO_PATH = Path("docs/TODO.md")
_BACKUP_SUBDIR = "todo.bk"


def backup(todo_path: Optional[Path] = None) -> None:
    """
    Backup TODO.md to a timestamped file in docs/todo.bk/.

    Args:
        todo_path: Path to TODO.md. Defaults to ./docs/TODO.md.
    """
    todo_path = todo_path or _DEFAULT_TODO_PATH

    if not todo_path.exists():
        print(f"No TODO.md found at {todo_path}. Nothing to backup.")
        return

    backup_dir = todo_path.parent / _BACKUP_SUBDIR
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"{timestamp}_TODO.md"
    shutil.copy2(todo_path, backup_path)
    print(f"✓ Backed up TODO.md to {backup_path}")


def main() -> None:
    """Standalone entry point."""
    backup()


if __name__ == "__main__":
    main()

```
