# pack-kit project structure
# Run: treekit packkit-tree.md --output ~/projects/dev-utils/python

```
packkit/
├── src/
│   └── packkit/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── collector.py
│       ├── packer.py
│       ├── shipper.py
│       └── exceptions.py
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_collector.py
│   ├── test_packer.py
│   └── test_shipper.py
├── data/
│   └── packkit.yaml.template   # example config template
├── pyproject.toml
└── README.md
```
