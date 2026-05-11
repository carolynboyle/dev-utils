# pkg_structure.md

**Path:** python/fletcher/docs/pkg_structure.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
fletcher/
├── pyproject.toml                    # Package metadata, entry point, dependencies
├── README.md                         # Package documentation
├── LICENSE                           # (MIT or your chosen license)
│
└── fletcher/                         # Python package directory
    ├── __init__.py                   # Public API exports
    ├── fletcher.py                   # Main CLI logic & manifest building
    ├── exceptions.py                 # Exception hierarchy (NEW)
    │
    └── data/                         # Configuration defaults (future)
        └── (empty for now, reserved for future defaults)


═══════════════════════════════════════════════════════════════════════════════

KEY CHANGES FROM CURRENT STRUCTURE:

BEFORE:
  fletcher/
  ├── __init__.py
  ├── fletcher.py
  └── (no exceptions.py)

AFTER:
  fletcher/
  ├── __init__.py           ← unchanged
  ├── fletcher.py           ← refactored (now raises exceptions)
  └── exceptions.py         ← NEW (exception hierarchy)


═══════════════════════════════════════════════════════════════════════════════

FILE LOCATIONS IN YOUR dev-utils REPO:

Your structure (from memory):
  dev-utils/
  └── python/
      ├── fletcher/
      │   ├── pyproject.toml
      │   ├── README.md
      │   └── fletcher/              ← Package dir
      │       ├── __init__.py
      │       ├── fletcher.py        ← Main module
      │       └── exceptions.py      ← NEW: Goes here
      │
      ├── mcpkit/
      │   └── ...
      │
      ├── menukit/
      │   └── ...
      │
      └── dbkit/
          └── ...


═══════════════════════════════════════════════════════════════════════════════

INSTALLATION & ENTRY POINT:

The pyproject.toml already has:
  [project.scripts]
  fletcher = "fletcher.fletcher:main"

This means:
  - Package name: "fletcher"
  - Module: "fletcher.fletcher"  (the module at fletcher/fletcher.py)
  - Function: "main"             (the main() function in that module)

After install, users run:
  $ fletcher --help
  $ fletcher --branch main


═══════════════════════════════════════════════════════════════════════════════

IMPORT PATHS (INSIDE THE PACKAGE):

In fletcher/fletcher.py:
  from fletcher.exceptions import (
      FletcherError,
      GitBranchError,
      ManifestNotFoundError,
      ManifestInvalidError,
  )

In fletcher/__init__.py:
  from fletcher.fletcher import build_url_manifest, write_manifest, main
  from fletcher.exceptions import FletcherError  # If you want to export it


═══════════════════════════════════════════════════════════════════════════════

CHECKLIST FOR MOVING TO GITHUB:

Place these files:
  ✓ fletcher/pyproject.toml          (already exists, no changes)
  ✓ fletcher/README.md               (already exists, no changes)
  ✓ fletcher/fletcher/__init__.py    (already exists, no changes)
  ✓ fletcher/fletcher/fletcher.py    (REPLACE with refactored version)
  ✓ fletcher/fletcher/exceptions.py  (NEW — create from provided code)

Verify:
  $ cd ~/projects/dev-utils/python/fletcher
  $ python -m py_compile fletcher/fletcher.py fletcher/exceptions.py
  $ pip install -e .
  $ fletcher --help

═══════════════════════════════════════════════════════════════════════════════

FUTURE EXPANSION (NOT NOW):

If fletcher grows to need git utilities in multiple packages, promote to:

  dev-utils/
  └── python/
      ├── devutils-git/              ← New personal library package
      │   ├── pyproject.toml
      │   └── devutils_git/
      │       ├── __init__.py
      │       └── git.py              ← get_confirmed_branch(), etc.
      │
      └── fletcher/
          └── fletcher/
              └── fletcher.py         ← imports from devutils_git
              └── exceptions.py       ← keeps its own FletcherError hierarchy

Then update fletcher's dependencies:
  [project]
  dependencies = [
      "pyyaml>=6.0",
      "devutils-git>=0.1.0",       ← NEW
  ]

But not now. Keep it simple in fletcher for now.
```
