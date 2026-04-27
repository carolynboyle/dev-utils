"""
viewkit.onthefly.config - Configuration loader for the OTF query tool.

Reads the 'viewkit:' section from ~/.config/dev-utils/config.yaml
and returns paths needed by the OTF tool.

The dev-utils config.yaml is the single source of truth for all
Project Crew tool configuration. OTF does not maintain its own
top-level config file.

Usage:
    from viewkit.onthefly.config import OTFConfig

    cfg = OTFConfig()
    queries_dir = cfg.queries_dir
    log_dir = cfg.log_dir
"""

from pathlib import Path
from typing import Optional

import yaml

from viewkit.onthefly.exceptions import OTFConfigError


_CONFIG_PATH = Path.home() / ".config" / "dev-utils" / "config.yaml"


class OTFConfig:
    """
    Loads OTF configuration from the dev-utils config.yaml.

    Reads the 'viewkit:' section and exposes the paths OTF needs.
    Raises OTFConfigError at construction time if anything is missing
    or invalid — fail fast, no lazy errors later.

    Args:
        config_path: Override config file path. Defaults to
                     ~/.config/dev-utils/config.yaml.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._path = config_path or _CONFIG_PATH
        cfg = self._load()
        self.queries_dir = Path(cfg["queries_dir"]).expanduser()
        self.log_dir = Path(cfg["log_dir"]).expanduser()

    def _load(self) -> dict:
        """
        Load and validate the viewkit: section from config.yaml.

        Returns:
            Dict containing 'queries_dir' and 'log_dir'.

        Raises:
            OTFConfigError: If the file is missing, unreadable, the
                            viewkit: section is absent, or required
                            keys are missing.
        """
        if not self._path.exists():
            raise OTFConfigError(
                f"Config file not found: {self._path}"
            )

        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise OTFConfigError(
                f"Could not read config file {self._path}: {exc}"
            ) from exc

        if not data or "viewkit" not in data:
            raise OTFConfigError(
                f"No 'viewkit:' section found in {self._path}. "
                f"Add a viewkit: block with queries_dir and log_dir."
            )

        cfg = data["viewkit"]
        missing = [k for k in ("queries_dir", "log_dir") if k not in cfg]
        if missing:
            raise OTFConfigError(
                f"Missing required viewkit config keys: {', '.join(missing)}"
            )

        return cfg
