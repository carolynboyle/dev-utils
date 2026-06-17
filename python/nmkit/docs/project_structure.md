```
nmkit/
├── src/
│   └── nmkit/
│       ├── __init__.py
│       ├── __main__.py      # entry point, calls assets.check() first
│       ├── assets.py        # font file presence check + download
│       ├── config.py        # loads nmkit.yaml + connections.yaml
│       ├── icons.py         # QPainter icon generation, uses assets.fonts()
│       ├── launcher.py      # generates .nxs, launches nxclient
│       ├── ui.py            # main window (grid) + systray
│       ├── logger.py        # identical to pxkit
│       ├── exceptions.py    # NmkitError, NmkitLaunchError
│       └── data/
│           ├── nmkit.yaml
│           ├── connections.yaml
│           └── fonts/       # empty in repo, populated by assets.py
├── docs/
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_launcher.py
│   ├── test_icons.py
│   └── test_assets.py
└── pyproject.toml
```
