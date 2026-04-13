# pyproject.toml

**Path:** python/menukit/pyproject.toml
**Syntax:** toml
**Generated:** 2026-04-13 14:09:28

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

# Install from this directory:
#   cd ~/projects/dev-utils/python/menukit
#   pip install -e .

[project]
name = "menukit"
version = "0.1.0"
description = "YAML-driven menu system and input plugin interface for CLI applications"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["menukit*"]
```
