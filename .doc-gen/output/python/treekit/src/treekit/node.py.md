# node.py

**Path:** python/treekit/src/treekit/node.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
node.py — Tree node dataclass for treekit.

Each Node represents a single file or directory entry parsed from a
markdown tree structure. The parser produces a tree of Nodes; the
builder consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    """
    A single entry in a parsed directory tree.

    Attributes:
        name:     Filename or directory name only — no path component.
        is_dir:   True if this entry represents a directory.
        depth:    Zero-based nesting depth, determined during parsing.
        children: Ordered list of child Nodes (directories and files).
        comment:  Inline comment stripped from the source line, if present.
    """

    name: str
    is_dir: bool
    depth: int
    children: list[Node] = field(default_factory=list)
    comment: Optional[str] = None

    def add_child(self, child: Node) -> None:
        """Append a child Node to this node's children list."""
        self.children.append(child)

    def __eq__(self, other: object) -> bool:
        """
        Compare two Nodes by structure and content.

        Nodes are equal if they have the same name, type, depth, comment,
        and recursively equal children. Comment comparison is included so
        round-trip tests can verify comment preservation if needed.

        Args:
            other: Object to compare against.

        Returns:
            True if both nodes are structurally identical.
        """
        if not isinstance(other, Node):
            return NotImplemented
        return (
            self.name == other.name
            and self.is_dir == other.is_dir
            and self.depth == other.depth
            and self.comment == other.comment
            and self.children == other.children
        )

    def __len__(self) -> int:
        """Return the number of direct children of this node."""
        return len(self.children)

    def __repr__(self) -> str:
        kind = "dir" if self.is_dir else "file"
        return f"Node({self.name!r}, {kind}, depth={self.depth})"

```
