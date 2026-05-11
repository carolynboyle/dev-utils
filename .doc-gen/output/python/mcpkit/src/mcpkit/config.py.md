# config.py

**Path:** python/mcpkit/src/mcpkit/config.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
mcpkit.config - Configuration management for mcpkit.

Loads mcpkit-config.yaml from ~/.config/dev-utils/ and provides
validated access to server, ollama, logging, and handler settings.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mcpkit.exceptions import ConfigError
from mcpkit.utils import expand_path


class Config:
    """
    Load and manage mcpkit configuration.

    Reads from ~/.config/dev-utils/mcpkit-config.yaml by default,
    or a custom path if provided.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config from file.

        Args:
            config_path: Path to mcpkit-config.yaml. If None, defaults to
                        ~/.config/dev-utils/mcpkit-config.yaml

        Raises:
            ConfigError: If file not found, invalid YAML, or required fields missing
        """
        if config_path is None:
            config_path = Path.home() / ".config" / "dev-utils" / "mcpkit-config.yaml"

        self.config_path = expand_path(config_path)
        self.data = self._load_yaml()
        self._validate()

    def _load_yaml(self) -> Dict[str, Any]:
        """
        Load YAML config file.

        Returns:
            Parsed YAML as dict

        Raises:
            ConfigError: If file not found or invalid YAML
        """
        if not self.config_path.exists():
            raise ConfigError(
                f"Config file not found: {self.config_path}\n"
                f"Expected: ~/.config/dev-utils/mcpkit-config.yaml"
            )

        try:
            content = self.config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if not data or not isinstance(data, dict):
                raise ConfigError(
                    f"Config file is empty or invalid: {self.config_path}"
                )
            return data
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {self.config_path}: {e}")
        except OSError as e:
            raise ConfigError(f"Could not read {self.config_path}: {e}")

    def _validate(self) -> None:
        """
        Validate that required config sections and fields exist.

        Required fields:
        - server.host, server.port
        - ollama.host, ollama.port
        - logging.level

        Raises:
            ConfigError: If required sections or fields are missing
        """
        required_sections = {
            "server": ["host", "port"],
            "ollama": ["host", "port"],
            "logging": ["level"],
        }

        for section, keys in required_sections.items():
            if section not in self.data:
                raise ConfigError(
                    f"Missing required section: [{section}]\n"
                    f"Check {self.config_path}"
                )

            for key in keys:
                if key not in self.data[section]:
                    raise ConfigError(
                        f"Missing required field: {section}.{key}\n"
                        f"Check {self.config_path}"
                    )

    # -- Server config --------------------------------------------------------

    def server_host(self) -> str:
        """Get MCP server host."""
        return self.data["server"]["host"]

    def server_port(self) -> int:
        """Get MCP server port."""
        return int(self.data["server"]["port"])

    def server_debug(self) -> bool:
        """Get debug mode setting. Defaults to False if not set."""
        return self.data.get("server", {}).get("debug", False)

    # -- Ollama config --------------------------------------------------------

    def ollama_host(self) -> str:
        """Get Ollama host."""
        return self.data["ollama"]["host"]

    def ollama_port(self) -> int:
        """Get Ollama port."""
        return int(self.data["ollama"]["port"])

    def ollama_timeout(self) -> int:
        """Get Ollama request timeout in seconds. Defaults to 120."""
        return self.data.get("ollama", {}).get("timeout_seconds", 120)

    def ollama_retries(self) -> int:
        """Get number of retry attempts for Ollama calls. Defaults to 3."""
        return self.data.get("ollama", {}).get("retry_attempts", 3)

    def ollama_url(self) -> str:
        """Get full Ollama API URL."""
        host = self.ollama_host()
        port = self.ollama_port()
        return f"http://{host}:{port}"

    # -- Logging config -------------------------------------------------------

    def log_level(self) -> str:
        """Get logging level (debug, info, warning, error)."""
        return self.data["logging"]["level"].lower()

    def log_file(self) -> Path:
        """Get path to log file. Defaults to ~/.local/share/mcpkit/mcpkit.log"""
        log_file_str = self.data.get("logging", {}).get(
            "file", "~/.local/share/mcpkit/mcpkit.log"
        )
        return expand_path(log_file_str)

    def log_format(self) -> str:
        """Get log message format string."""
        default_format = "%(asctime)s | %(levelname)-8s | %(message)s"
        return self.data.get("logging", {}).get("format", default_format)

    # -- Handler config -------------------------------------------------------

    def handler_modules(self) -> List[str]:
        """
        Get list of handler module paths to import.

        Defaults to built-in handlers if not specified.
        """
        return self.data.get(
            "handler_modules",
            [
                "mcpkit.handlers.builtins",
                "mcpkit.handlers.models",
            ],
        )

    # -- Raw access -----------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get raw config value by dot-notation key.

        Example:
            config.get("ollama.host") → "localhost"

        Args:
            key: Dot-notation key (e.g., "ollama.host", "server.port")
            default: Value if key not found

        Returns:
            Config value or default
        """
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

```
