# pxkit project structure

```
pxkit/
├── src/
│   └── pxkit/
│       ├── __init__.py
│       ├── __main__.py         # entry point
│       ├── config.py           # loads YAML, applies user overrides
│       ├── launcher.py         # open browser / launch virt-viewer
│       ├── connection.py       # Proxmox API calls, SPICE ticket retrieval
│       ├── ui.py               # tkinter dialog, calls launcher only
│       └── data/
│           └── pxkit.yaml      # shipped defaults
├── docs/
│   └── project_structure.md
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_launcher.py
│   └── test_connection.py
└── pyproject.toml
```
