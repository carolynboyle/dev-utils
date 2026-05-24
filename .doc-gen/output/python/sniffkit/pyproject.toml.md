# pyproject.toml

**Path:** python/sniffkit/pyproject.toml
**Syntax:** toml
**Generated:** 2026-05-20 15:41:52

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sniffkit"
version = "0.1.0"
description = "Content-type detector and file classifier for raw text output"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
sniffkit = "sniffkit.classifier:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["sniffkit*"]

```
