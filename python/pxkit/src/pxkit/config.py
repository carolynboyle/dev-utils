"""
pxkit.config - Configuration management for pxkit.

Loads user configuration from ~/.config/pxkit/pxkit.yaml. This file
is written by install.sh and is required — pxkit raises PxkitConfigError
if it does not exist, directing the user to run install.sh.

The shipped pxkit/data/pxkit.yaml is a schema reference only and is
not loaded at runtime.

Usage:
    from pxkit.config import ConfigManager

    config = ConfigManager()
    servers = config.servers
    server  = config.get_server("t490")
    vms     = config.vms
"""

from pathlib import Path
from typing import Optional

import yaml

from pxkit.exceptions import PxkitConfigError


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR    = Path(__file__).parent / "data"
_USER_CONFIG = Path.home() / ".config" / "pxkit" / "pxkit.yaml"


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Loads pxkit user configuration.

    Requires ~/.config/pxkit/pxkit.yaml to exist. Run install.sh to
    create it. Raises PxkitConfigError if the file is missing.

    Usage:
        config = ConfigManager()
        server = config.get_server("t490")
        for vm in config.vms:
            print(vm['name'])
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise ConfigManager.

        Args:
            config_path: Override path to the user config file. Defaults
                         to ~/.config/pxkit/pxkit.yaml. Useful for testing.
        """
        self._config = self._load(config_path)

    # -- Public interface -----------------------------------------------------

    @property
    def servers(self) -> list:
        """
        List of configured Proxmox servers.

        Returns:
            List of server dicts, each with keys: name, host, port,
            node, token_id. Token secret is never stored here.
        """
        return self._config.get("servers", [])

    def get_server(self, name: str) -> dict:
        """
        Look up a server by name.

        Args:
            name: Server name as defined in pxkit.yaml.

        Returns:
            Server dict with keys: name, host, port, node, token_id.

        Raises:
            PxkitConfigError: If no server with that name is found.
        """
        for server in self.servers:
            if server.get("name") == name:
                return server
        available = ", ".join(s.get("name", "?") for s in self.servers)
        raise PxkitConfigError(
            f"Server '{name}' not found in config. "
            f"Available servers: {available}"
        )

    @property
    def vms(self) -> list:
        """
        List of configured VMs.

        Returns:
            List of VM dicts, each with keys: name, vmid, server,
            connection (type, host, port, security).
        """
        return self._config.get("vms", [])

    def get(self, key: str, default=None):
        """
        Return a value from the pxkit config section by key.

        Args:
            key:     Top-level key within the pxkit section.
            default: Value to return if the key is absent.

        Returns:
            The config value, or default if not found.
        """
        return self._config.get(key, default)

    # -- Internal -------------------------------------------------------------

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """
        Load user config from ~/.config/pxkit/pxkit.yaml.

        No default fallback — a user config is required. If it doesn't
        exist, the user is directed to run install.sh.

        Args:
            config_path: Explicit user config path override, or None
                         to use ~/.config/pxkit/pxkit.yaml.

        Returns:
            Parsed pxkit config dict.

        Raises:
            PxkitConfigError: If the user config does not exist, or
                              cannot be read or parsed.
        """
        user_path = config_path or _USER_CONFIG

        if not user_path.exists():
            raise PxkitConfigError(
                f"No pxkit configuration found at {user_path}.\n"
                f"Run install.sh to set up pxkit and configure your servers."
            )

        return ConfigManager._load_section(user_path, "pxkit")

    @staticmethod
    def _load_section(path: Path, section: str) -> dict:
        """
        Load a named top-level section from a YAML file.

        Args:
            path:    Path to the YAML file.
            section: Top-level section key to extract.

        Returns:
            Dict of key/value pairs from the section, or empty dict
            if the section is absent.

        Raises:
            PxkitConfigError: If the file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise PxkitConfigError(
                f"Could not read config file {path}: {exc}"
            ) from exc

        if not data or not isinstance(data, dict):
            return {}

        return data.get(section, {})
