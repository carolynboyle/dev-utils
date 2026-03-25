# do_todo.py

**Path:** src/todo/do_todo.py
**Syntax:** python
**Generated:** 2026-03-25 09:32:34

```python
#!/usr/bin/env python3
"""
todo.do_todo - Interactive TODO.md generator.

Prompts for items until user enters 'q', 'quit', or 'done'.
Writes to docs/TODO.md in the current directory.

Standalone usage:
    do-todo

Plugin usage: invoked by projs tools menu via entry point.
"""

import os


TODO_FILE = "docs/TODO.md"


def main():
    """Interactive TODO.md generator entry point."""
    os.makedirs("docs", exist_ok=True)

    print("Enter TODO items. Type 'q', 'quit', or 'done' to finish.\n")

    items = []
    while True:
        item = input(f"Item {len(items) + 1}: ").strip()
        if item.lower() in {"q", "quit", "done"}:
            break
        if item:
            items.append(item)

    if not items:
        print("No items entered. Exiting.")
        return

    with open(TODO_FILE, "w", encoding="utf-8") as f:
        f.write("# TODO\n\n")
        for i, task in enumerate(items, start=1):
            f.write(f"{i}. {task}\n")

    print(f"\nTODO.md written with {len(items)} items at {TODO_FILE}")


if __name__ == "__main__":
    main()

```
