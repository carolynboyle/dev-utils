# project structure

**Path:** python/contactkit/docs/project structure
**Syntax:** text
**Generated:** 2026-05-11 15:11:09

```
contactkit/
├── pyproject.toml
├── src/contactkit/
│   ├── __init__.py
│   ├── config.py              # ConfigManager for DB connection
│   ├── logger.py              # fletcher-style logging
│   ├── cli.py                 # entry point
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py            # BaseImporter abstract class
│   │   └── imports/
│   │       ├── __init__.py
│   │       ├── gmail/
│   │       │   ├── __init__.py
│   │       │   ├── importer.py
│   │       │   ├── config.yaml (future — field mappings, etc.)
│   │       │   └── README.md
│   │       ├── proton/
│   │       │   ├── __init__.py
│   │       │   ├── importer.py
│   │       │   ├── config.yaml
│   │       │   └── README.md
│   │       ├── outlook/
│   │       └── apple/
│   └── importer.py            # Orchestrator
├── tests/
│   ├── test_importer.py
│   └── test_plugins/
│       ├── test_gmail.py
│       └── ...
└── README.md
```
