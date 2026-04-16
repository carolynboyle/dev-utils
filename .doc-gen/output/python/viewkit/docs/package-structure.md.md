# package-structure.md

**Path:** python/viewkit/docs/package-structure.md
**Syntax:** markdown
**Generated:** 2026-04-16 10:47:57

```markdown
python/viewkit/
├── pyproject.toml
├── viewkit/
│   ├── __init__.py
│   ├── view_builder.py        # ViewBuilder class — loads views.yaml, returns view defs
│   ├── models.py              # FieldDef, ColumnDef, ViewDef dataclasses
│   └── exceptions.py         # ViewKitError, ViewNotFoundError
└── tests/
    └── test_view_builder.py
```
