# install.py

**Path:** python/_install/install.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
Module for managing the installation of dev-utils packages.

This script reads a YAML configuration file to batch-install Python packages
in editable mode into a shared network virtual environment.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict
import yaml


def install_packages(config_name: str = 'install_config.yaml') -> None:
    """
    Read configuration and install packages via pip in editable mode.

    Args:
        config_name: The filename of the YAML config located in the script's directory.

    Raises:
        FileNotFoundError: If the config file is missing.
        yaml.YAMLError: If the YAML file is malformed.
        subprocess.CalledProcessError: If a pip install command fails.
    """
    # 1. Define paths FIRST
    script_dir = Path(__file__).parent
    config_path = script_dir / config_name

    # 2. Check for file existence
    if not config_path.exists():
        print(f"Error: Configuration file '{config_name}' not found.")
        print("Please copy 'install_config.yaml.template' to 'install_config.yaml' and edit it.")
        return

    # 3. Proceed with reading
    with open(config_path, 'r', encoding='utf-8') as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    settings = config.get('settings', {})
    pip_bin = settings.get('venv_executable')
    base_source_path = settings.get('base_source_path')
    packages = config.get('packages', [])

    if not pip_bin or not base_source_path:
        raise ValueError("Missing 'settings' in configuration file.")

    base_path = Path(base_source_path)

    for pkg in packages:
        pkg_path = base_path / pkg
        print(f"--- Installing {pkg} ---")
        try:
            # Use check=True to raise an error if the install fails
            subprocess.run([pip_bin, "install", "-e", str(pkg_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to install {pkg}. Exit code: {e.returncode}")


if __name__ == "__main__":
    install_packages()
```
