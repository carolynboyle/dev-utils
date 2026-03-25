# pyproject.toml

**Path:** pyproject.toml
**Syntax:** toml
**Generated:** 2026-03-25 09:32:34

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "todo"
version = "0.1.0"
description = "Simple interactive TODO.md generator and backup tool"
requires-python = ">=3.8"

[project.scripts]
do-todo = "todo.do_todo:main"
backup-todo = "todo.backup_todo:main"

[tool.setuptools.packages.find]
where = ["src"]

```
