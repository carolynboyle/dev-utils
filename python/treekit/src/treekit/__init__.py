"""
treekit — Create directory trees from markdown structure specifications.

Public API:
    TreeParser   — parses markdown text into a Node tree
    TreeBuilder  — creates the filesystem tree from a Node tree
    Node         — tree node dataclass
    BuildResult  — result dataclass returned by TreeBuilder.build()

Exceptions:
    TreekitError       — base class for all treekit exceptions
    ParseError         — base class for parser exceptions
    EmptyInputError    — input is empty
    NoTreeFoundError   — no recognisable tree structure in input
    BuildError         — base class for builder exceptions
    OutputPathError    — output path missing or not a directory
    PathCollisionError — type mismatch between expected and existing path
    TkPermissionError  — permission denied during filesystem operation
    LogError           — log write failed
"""

from treekit.builder import BuildResult, TreeBuilder
from treekit.exceptions import (
    BuildError,
    EmptyInputError,
    LogError,
    NoTreeFoundError,
    OutputPathError,
    ParseError,
    PathCollisionError,
    TkPermissionError,
    TreekitError,
)
from treekit.node import Node
from treekit.parser import TreeParser

__all__ = [
    "TreeParser",
    "TreeBuilder",
    "Node",
    "BuildResult",
    "TreekitError",
    "ParseError",
    "EmptyInputError",
    "NoTreeFoundError",
    "BuildError",
    "OutputPathError",
    "PathCollisionError",
    "TkPermissionError",
    "LogError",
]
