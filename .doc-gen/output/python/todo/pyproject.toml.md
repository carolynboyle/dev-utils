# pyproject.toml

**Path:** python/todo/pyproject.toml
**Syntax:** toml
**Generated:** 2026-04-13 14:09:28

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "todo"
version = "0.1.0"
description = "Simple interactive TODO.md generator and backup tool"
requires-python = ">=3.8"

[project.scripts]
do-todo = "todo.todo:main"
backup-todo = "todo.backup_todo:main"

[tool.setuptools.packages.find]
where = ["src"]

```
