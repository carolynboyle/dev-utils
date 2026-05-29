# ptykit — config.py Changeset (revised)

**File:** `ptykit/config.py`
**Status:** New file (empty → implemented)

---

## Why This First

`config.py` has no dependencies on any other ptykit module. Every
other module depends on it. Build it first, test it first.

---

## BEFORE

```python
# empty
```

---

## AFTER

```python
"""
ptykit/config.py

Loads ptykit configuration from ~/.config/dev-utils/ptykit/<program>.yaml.

This is the single source of truth for all paths used by ptykit.
Other modules import ConfigLoader rather than hardcoding paths.

Config file location:
    ~/.config/dev-utils/ptykit/<program>.yaml

Config structure:
    program: advent

    intercept:
      - map
      - hint

    plugins:
      - ptykit_ccc.map_plugin:MapPlugin

Usage:
    from ptykit.config import ConfigLoader

    config = ConfigLoader("advent")
    print(config.program)
    print(config.intercept)
    print(config.plugins)
"""

from pathlib import Path

import yaml

from ptykit.exceptions import PtyKitConfigError


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path.home() / ".config" / "dev-utils" / "ptykit"


def config_path(program: str) -> Path:
    """
    Return the path to a program's ptykit config yaml.

    Args:
        program: Program name (e.g. 'advent').

    Returns:
        Path to ~/.config/dev-utils/ptykit/<program>.yaml
    """
    return _CONFIG_DIR / f"{program}.yaml"


# ---------------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------------

class ConfigLoader:
    """
    Loads a ptykit YAML config file and provides typed accessors.

    Config is read from ~/.config/dev-utils/ptykit/<program>.yaml.
    An explicit path can be supplied for testing or container use.

    Raises PtyKitConfigError on missing file, parse failure, or
    missing required fields.
    """

    REQUIRED_FIELDS = ("program", "intercept", "plugins")

    def __init__(self, program: str, config_file: Path | None = None) -> None:
        """
        Load config for a named program.

        Args:
            program:     The CLI program name (e.g. 'advent'). Used to
                         locate ~/.config/dev-utils/ptykit/<program>.yaml
                         unless config_file is supplied.
            config_file: Explicit path override. Useful for containers
                         and tests.
        """
        self._path = config_file or config_path(program)
        self._data = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            raise PtyKitConfigError(f"Config file not found: {self._path}")

        try:
            with open(self._path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PtyKitConfigError(
                f"Failed to parse config file: {e}"
            ) from e

        if not isinstance(data, dict):
            raise PtyKitConfigError(
                f"Config file must be a YAML mapping, "
                f"got: {type(data).__name__}"
            )

        self._validate(data)
        return data

    def _validate(self, data: dict) -> None:
        missing = [f for f in self.REQUIRED_FIELDS if f not in data]
        if missing:
            raise PtyKitConfigError(
                f"Config file missing required fields: {', '.join(missing)}"
            )

        if not isinstance(data["intercept"], list):
            raise PtyKitConfigError(
                "'intercept' must be a list of command strings"
            )

        if not isinstance(data["plugins"], list):
            raise PtyKitConfigError(
                "'plugins' must be a list of plugin paths"
            )

    @property
    def program(self) -> str:
        """The CLI program to wrap. Must be on PATH or a full path."""
        return self._data["program"]

    @property
    def intercept(self) -> list[str]:
        """
        List of commands to intercept, normalised to lowercase.
        Matched case-insensitively against trimmed stdin input.
        """
        return [cmd.lower() for cmd in self._data["intercept"]]

    @property
    def plugins(self) -> list[str]:
        """
        List of dotted plugin paths in the form:
            module.submodule:ClassName
        """
        return self._data["plugins"]
```

---

## Why

**`config_path(program)`** — module-level function, not a method.
Shared by `ConfigLoader` and `initialize.py` so both agree on where
configs live without duplicating the path logic.

**`config_file` override** — explicit path for containers (where the
YAML ships with the container) and tests. Container CMD can pass
`--config /home/ccc/ptykit_ccc/data/config.yaml` and bypass the
default location entirely.

**`PtyKitConfigError`** — named exception from `ptykit.exceptions`
(see exceptions.py changeset). Mirrors setupkit's pattern exactly.

**`intercept` normalised to lowercase** — commands are matched
case-insensitively at intercept time. Normalising at load time means
the comparison in `wrapper.py` is always a simple `==`.

**`yaml.safe_load`** — never `yaml.load`.

---

## Tests

**File:** `tests/test_config.py`

```python
"""
tests/test_config.py

Tests for ptykit.config.ConfigLoader.
"""

import pytest
import yaml
from pathlib import Path
from ptykit.config import ConfigLoader, config_path
from ptykit.exceptions import PtyKitConfigError


@pytest.fixture
def valid_config(tmp_path):
    config = {
        "program": "advent",
        "intercept": ["map", "hint"],
        "plugins": ["ptykit_ccc.map_plugin:MapPlugin"],
    }
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    return path


def test_loads_valid_config(valid_config):
    loader = ConfigLoader("advent", config_file=valid_config)
    assert loader.program == "advent"
    assert loader.intercept == ["map", "hint"]
    assert loader.plugins == ["ptykit_ccc.map_plugin:MapPlugin"]


def test_intercept_normalised_to_lowercase(tmp_path):
    config = {
        "program": "advent",
        "intercept": ["MAP", "Hint"],
        "plugins": [],
    }
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    loader = ConfigLoader("advent", config_file=path)
    assert loader.intercept == ["map", "hint"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(PtyKitConfigError, match="not found"):
        ConfigLoader("advent", config_file=tmp_path / "missing.yaml")


def test_missing_required_field_raises(tmp_path):
    config = {"program": "advent", "intercept": ["map"]}  # missing plugins
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="missing required fields"):
        ConfigLoader("advent", config_file=path)


def test_invalid_yaml_raises(tmp_path):
    path = tmp_path / "advent.yaml"
    path.write_text(":::: not valid yaml ::::", encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="Failed to parse"):
        ConfigLoader("advent", config_file=path)


def test_intercept_not_list_raises(tmp_path):
    config = {"program": "advent", "intercept": "map", "plugins": []}
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="must be a list"):
        ConfigLoader("advent", config_file=path)


def test_config_path_returns_correct_location():
    p = config_path("advent")
    assert p.name == "advent.yaml"
    assert "dev-utils" in str(p)
    assert "ptykit" in str(p)
```

---

## Checklist

- [ ] `ptykit/config.py` written
- [ ] `ptykit/exceptions.py` written (dependency — see exceptions changeset)
- [ ] `tests/test_config.py` written
- [ ] `pytest tests/test_config.py` passes
- [ ] `pylint ptykit/config.py` passes clean
