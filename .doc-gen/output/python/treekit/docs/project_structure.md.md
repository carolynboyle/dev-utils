# project_structure.md

**Path:** python/treekit/docs/project_structure.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# treekit: Canonical Project Structure

Last updated: 2026-05-11

This document is the authoritative reference for the project directory structure.
Update it when the structure changes. Do not let it drift from the actual repo.

---

## Full Directory Tree

```
treekit/
├── .gitignore
├── docs/
│   └── project_structure.md
├── LICENSE
├── pyproject.toml
├── README.md
├── src/
│   └── treekit/
│       ├── __init__.py
│       ├── builder.py
│       ├── cli.py
│       ├── exceptions.py
│       ├── node.py
│       └── parser.py
└── tests/
    ├── conftest.py
    ├── test_builder.py
    ├── test_cli.py
    ├── test_exceptions.py
    ├── test_node.py
    └── test_parser.py
```

---

## Notes

- `treekit.yaml` (setupkit plugin manifest) lives at
  `~/.config/dev-utils/setupkit/treekit.yaml` — it is a local machine
  config, not a source file, and is not committed to the repo.
- `LICENSE` — MIT license. Required by pyproject.toml.
- Build artifacts (`*.egg-info/`, `__pycache__/`, `dist/`) are excluded
  by `.gitignore` and never committed.

```
