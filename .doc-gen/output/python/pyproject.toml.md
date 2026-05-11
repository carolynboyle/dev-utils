# pyproject.toml

**Path:** python/pyproject.toml
**Syntax:** toml
**Generated:** 2026-05-11 15:11:09

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dev-utils"
version = "0.1.0"
description = "Internal toolset for devshare environments"
dependencies = [
    "PyYAML>=6.0",
]

[tool.setuptools]
# This ensures that 'pip install .' doesn't try to package 
# the sub-tools as one giant library, but allows the 
# environment to satisfy the PyYAML requirement.
packages = []
```
