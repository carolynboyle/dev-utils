# pyproject.toml

**Path:** python/mcpkit/pyproject.toml
**Syntax:** toml
**Generated:** 2026-04-16 10:47:57

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "mcpkit"
version = "0.1.0"
description = "YAML-driven MCP server framework for automating workflows with LLMs"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    { name = "Carolyn Boyle" }
]
license = { text = "MIT" }

dependencies = [
    "pyyaml>=6.0",
    "requests>=2.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pylint>=3.0",
]

[tool.setuptools.packages.find]
where = ["src"]
include = ["mcpkit*"]

[tool.setuptools.package-data]
mcpkit = ["data/**/*.yaml", "data/**/*.json"]

[tool.pylint.messages_control]
disable = [
    "C0111",  # missing-docstring (we use docstrings selectively)
    "R0913",  # too-many-arguments (sometimes necessary)
    "R0914",  # too-many-locals (acceptable in complex functions)
]

[tool.pylint.format]
max-line-length = 120

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--strict-markers"

[tool.pytest.markers]
integration = "integration tests (require external resources like Ollama)"
slow = "slow tests"
```
