# conftest.py

**Path:** python/treekit/tests/conftest.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
conftest.py — Shared pytest fixtures for treekit tests.

The canonical test tree is a small, self-contained fictional project
structure owned entirely by the test suite. It is not tied to any real
project on disk.

Tree structure used throughout:

    test_project/
    ├── src/
    │   └── test_project/
    │       ├── __init__.py
    │       └── core.py            # Core module
    ├── tests/
    │   ├── __init__.py
    │   └── test_core.py
    ├── docs/                      # Documentation
    │   └── README.md
    └── pyproject.toml

Fixtures:
    fenced_markdown    — tree embedded in a fenced code block
    bare_markdown      — same tree as bare text, no fencing
    expected_tree      — hand-built Node tree; independent expected value
                         for parser assertions and future round-trip tests

Note for future companion tests:
    When the filesystem → markdown companion feature is added, the
    expected_tree fixture serves as the known-good reference for
    round-trip validation:
        tmp_path (built from expected_tree) → companion → markdown
        → TreeParser → Node tree == expected_tree
"""

import pytest

from treekit.node import Node


# -----------------------------------------------------------------------------
# Markdown fixtures
# -----------------------------------------------------------------------------

FENCED_MARKDOWN = """\
```
test_project/
├── src/
│   └── test_project/
│       ├── __init__.py
│       └── core.py            # Core module
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── docs/                      # Documentation
│   └── README.md
└── pyproject.toml
```
"""

BARE_MARKDOWN = """\
test_project/
├── src/
│   └── test_project/
│       ├── __init__.py
│       └── core.py            # Core module
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── docs/                      # Documentation
│   └── README.md
└── pyproject.toml
"""


@pytest.fixture
def fenced_markdown() -> str:
    """Markdown string with tree embedded in a fenced code block."""
    return FENCED_MARKDOWN


@pytest.fixture
def bare_markdown() -> str:
    """Markdown string with bare tree text, no fencing."""
    return BARE_MARKDOWN


# -----------------------------------------------------------------------------
# Expected Node tree
# -----------------------------------------------------------------------------

@pytest.fixture
def expected_tree() -> Node:
    """
    Hand-built Node tree matching the canonical test structure.

    This is the independent expected value used in parser assertions.
    It is also the reference for future round-trip tests when the
    filesystem → markdown companion feature is implemented.

    Returns:
        Root Node of the canonical test tree.
    """
    # --- Leaf nodes ----------------------------------------------------------

    src_init = Node(name='__init__.py', is_dir=False, depth=3)
    src_core = Node(name='core.py', is_dir=False, depth=3, comment='Core module')

    tests_init = Node(name='__init__.py', is_dir=False, depth=2)
    tests_core = Node(name='test_core.py', is_dir=False, depth=2)

    docs_readme = Node(name='README.md', is_dir=False, depth=2)

    pyproject = Node(name='pyproject.toml', is_dir=False, depth=1)

    # --- Inner src/test_project/ ---------------------------------------------

    inner_pkg = Node(name='test_project', is_dir=True, depth=2)
    inner_pkg.add_child(src_init)
    inner_pkg.add_child(src_core)

    # --- Top-level directories -----------------------------------------------

    src = Node(name='src', is_dir=True, depth=1)
    src.add_child(inner_pkg)

    tests = Node(name='tests', is_dir=True, depth=1)
    tests.add_child(tests_init)
    tests.add_child(tests_core)

    docs = Node(name='docs', is_dir=True, depth=1, comment='Documentation')
    docs.add_child(docs_readme)

    # --- Root ----------------------------------------------------------------

    root = Node(name='test_project', is_dir=True, depth=0)
    root.add_child(src)
    root.add_child(tests)
    root.add_child(docs)
    root.add_child(pyproject)

    return root

```
