# pyproject.toml

**Path:** python/fletcher/pyproject.toml
**Syntax:** toml
**Generated:** 2026-03-25 09:39:05

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

# Install from this directory:
#   cd ~/projects/dev-utils/python/fletcher
#   pip install -e .
#
# Or from anywhere:
#   pip install -e ~/projects/dev-utils/python/fletcher

[project]
name = "fletcher"
version = "0.1.0"
description = "GitHub URL manifest generator for dev-utils / Project Crew"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[project.scripts]
fletcher = "fletcher.fletcher:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["fletcher*"]

```
