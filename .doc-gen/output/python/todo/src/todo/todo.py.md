# todo.py

**Path:** python/todo/src/todo/todo.py
**Syntax:** python
**Generated:** 2026-04-13 14:09:28

```python
#!/usr/bin/env python3
"""
todo.todo - Todo list manager.

Manages per-project todo items stored as JSON, with markdown export.

Standalone usage (runs against current directory):
    do-todo

Plugin usage (called by projs with project context):
    from todo.todo import run
    run(project_name="myproject", project_path="/home/user/projects/myproject", config=...)

Storage:
    Standalone:  ~/.local/share/todo/todos.json
    Plugin:      ~/.projects/todos/<project>.json

Export:
    Standalone:  TODO.md in the directory do-todo was called from.
    Plugin:      docs/TODO.md relative to project path (or as configured
                 in ~/.projects/config/plugins.yaml).
    Auto-exported on exit — no need to select Export manually.
"""

import json
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STATUSES = ["open", "in progress", "on hold", "complete"]

_STATUS_DISPLAY = {
    "open":        "[ ]",
    "in progress": "[~]",
    "on hold":     "[!]",
    "complete":    "[x]",
}

_DEFAULT_OUTPUT_DIR = "docs"
_DEFAULT_FILENAME   = "TODO.md"
_BACKUP_SUBDIR      = "todo.bk"

_STANDALONE_JSON = Path.home() / ".local" / "share" / "todo" / "todos.json"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_todos(json_path: Path) -> List[Dict[str, Any]]:
    """Load todos from JSON file. Returns empty list if file doesn't exist."""
    if not json_path.exists():
        return []
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: could not load {json_path}: {exc}")
        return []


def _save_todos(json_path: Path, todos: List[Dict[str, Any]]) -> None:
    """Save todos to JSON file."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(todos, indent=2), encoding="utf-8")


def _next_id(todos: List[Dict[str, Any]]) -> int:
    """Return next available id."""
    if not todos:
        return 1
    return max(t["id"] for t in todos) + 1


def _find_by_id(todos: List[Dict[str, Any]], item_id: int) -> Optional[Dict[str, Any]]:
    """Find a todo item by id."""
    for t in todos:
        if t["id"] == item_id:
            return t
    return None


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def _export_markdown(
    todos: List[Dict[str, Any]],
    md_path: Path,
    project_path: Optional[Path] = None,
) -> None:
    """Write todos to a markdown file, grouped by status."""
    md_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    header_path = str(project_path) if project_path else str(Path.cwd())
    lines.append(f"# TODO — {header_path}\n")

    # Group by status in display order
    for status in VALID_STATUSES:
        items = [t for t in todos if t.get("status") == status]
        if not items:
            continue

        lines.append(f"\n## {status.title()}\n")
        for t in items:
            marker = _STATUS_DISPLAY.get(status, "[ ]")
            lines.append(f"- {marker} **[{t['id']}]** {t['description']}")
            if t.get("links"):
                for link in [l.strip() for l in t["links"].split(",") if l.strip()]:
                    lines.append(f"  - {link}")
            lines.append(f"  *created: {t.get('created', '—')}*")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Exported TODO.md to {md_path}")


def _backup_markdown(md_path: Path) -> None:
    """Backup existing TODO.md to <md_dir>/todo.bk/ before overwriting."""
    if not md_path.exists():
        return

    backup_dir = md_path.parent / _BACKUP_SUBDIR
    backup_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"{timestamp}_TODO.md"
    shutil.copy2(md_path, backup_path)
    print(f"  ↷ Backed up existing TODO.md to {backup_path.name}")


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _print_todos(todos: List[Dict[str, Any]]) -> None:
    """Print todos to terminal grouped by status."""
    if not todos:
        print("  No todo items.")
        return

    for status in VALID_STATUSES:
        items = [t for t in todos if t.get("status") == status]
        if not items:
            continue
        print(f"\n  {status.upper()}")
        for t in items:
            marker = _STATUS_DISPLAY.get(status, "[ ]")
            links = f"  → {t['links']}" if t.get("links") else ""
            print(f"    {marker} [{t['id']:>3}] {t['description']}{links}")


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _prompt_status(current: Optional[str] = None) -> str:
    """Prompt user to select a status."""
    print("\n  Status options:")
    for i, s in enumerate(VALID_STATUSES, 1):
        marker = " ←" if s == current else ""
        print(f"    {i}. {s}{marker}")

    while True:
        raw = input("  Selection: ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(VALID_STATUSES):
                return VALID_STATUSES[idx]
        except ValueError:
            pass
        print(f"  Please enter 1–{len(VALID_STATUSES)}.")


def _prompt_links(current: Optional[str] = None) -> str:
    """Prompt for comma-separated links."""
    if current:
        print(f"  Current links: {current}")
        print("  Enter new links to replace, or press Enter to keep current.")
    raw = input("  Links (comma-separated, or blank for none): ").strip()
    if not raw and current:
        return current
    return raw


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def add_item(
    todos: List[Dict[str, Any]],
    description: str,
    links: str = "",
) -> Dict[str, Any]:
    """Add a new todo item and return it."""
    item = {
        "id":          _next_id(todos),
        "description": description,
        "status":      "open",
        "created":     date.today().isoformat(),
        "links":       links,
    }
    todos.append(item)
    return item


def update_status(
    todos: List[Dict[str, Any]],
    item_id: int,
    status: str,
) -> bool:
    """Update the status of a todo item. Returns True if found."""
    item = _find_by_id(todos, item_id)
    if not item:
        return False
    item["status"] = status
    return True


def delete_item(todos: List[Dict[str, Any]], item_id: int) -> bool:
    """Delete a todo item by id. Returns True if found."""
    for i, t in enumerate(todos):
        if t["id"] == item_id:
            todos.pop(i)
            return True
    return False


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

def _interactive_menu(
    todos: List[Dict[str, Any]],
    json_path: Path,
    md_path: Path,
    project_path: Optional[Path] = None,
) -> None:
    """Interactive todo management loop."""
    while True:
        print("\n" + "=" * 50)
        print("TODO")
        print("=" * 50)
        _print_todos(todos)

        print("\n  1. Add item")
        print("  2. Update status")
        print("  3. Delete item")
        print("  4. Export TODO.md")
        print("  5. Done")

        raw = input("\n  Selection: ").strip()

        if raw == "1":
            desc = input("  Description: ").strip()
            if not desc:
                print("  Description cannot be empty.")
                continue
            links = _prompt_links()
            item = add_item(todos, desc, links)
            _save_todos(json_path, todos)
            print(f"  ✓ Added [{item['id']}] {item['description']}")

        elif raw == "2":
            if not todos:
                print("  No items to update.")
                continue
            try:
                item_id = int(input("  Item id: ").strip())
            except ValueError:
                print("  Please enter a number.")
                continue
            item = _find_by_id(todos, item_id)
            if not item:
                print(f"  Item {item_id} not found.")
                continue
            status = _prompt_status(current=item["status"])
            update_status(todos, item_id, status)
            _save_todos(json_path, todos)
            print(f"  ✓ [{item_id}] status → {status}")

        elif raw == "3":
            if not todos:
                print("  No items to delete.")
                continue
            try:
                item_id = int(input("  Item id: ").strip())
            except ValueError:
                print("  Please enter a number.")
                continue
            if not _find_by_id(todos, item_id):
                print(f"  Item {item_id} not found.")
                continue
            confirm = input(f"  Delete item {item_id}? [y/N]: ").strip().lower()
            if confirm == "y":
                delete_item(todos, item_id)
                _save_todos(json_path, todos)
                print(f"  ✓ Item {item_id} deleted.")

        elif raw == "4":
            _backup_markdown(md_path)
            _export_markdown(todos, md_path, project_path)

        elif raw in ("5", "q", "quit", "done", ""):
            # Auto-export on exit
            _backup_markdown(md_path)
            _export_markdown(todos, md_path, project_path)
            break

        else:
            print("  Please enter 1–5.")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run(
    project_name: Optional[str] = None,
    project_path: Optional[Path] = None,
    config=None,
) -> None:
    """
    Plugin entry point — called by projs with project context.

    Args:
        project_name:  Project name, used to locate JSON storage.
        project_path:  Absolute project path, used for markdown export header.
        config:        projs ConfigManager instance (reads plugins.yaml).
    """
    # Resolve JSON storage path
    if project_name and config:
        json_path = Path(config.root) / "todos" / f"{project_name}.json"
    elif project_name:
        json_path = Path.home() / ".projects" / "todos" / f"{project_name}.json"
    else:
        json_path = _STANDALONE_JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve markdown output path
    if project_name:
        output_dir = _DEFAULT_OUTPUT_DIR
        filename = _DEFAULT_FILENAME
        if config:
            try:
                plugins_cfg = config.plugins if hasattr(config, "plugins") else {}
                todo_cfg = plugins_cfg.get("todo", {})
                output_dir = todo_cfg.get("output_dir", _DEFAULT_OUTPUT_DIR)
                filename = todo_cfg.get("filename", _DEFAULT_FILENAME)
            except Exception:
                pass
        base = project_path or Path.cwd()
        md_path = base / output_dir / filename
    else:
        # Standalone: write TODO.md in cwd, no subdirectory
        md_path = Path.cwd() / _DEFAULT_FILENAME

    todos = _load_todos(json_path)
    _interactive_menu(todos, json_path, md_path, project_path)


def main() -> None:
    """
    Standalone entry point.

    JSON stored at ~/.local/share/todo/todos.json.
    TODO.md written to the current directory.
    """
    run()


if __name__ == "__main__":
    main()
```
