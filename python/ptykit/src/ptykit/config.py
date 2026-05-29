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
