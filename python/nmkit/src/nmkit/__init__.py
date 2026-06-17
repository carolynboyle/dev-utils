"""
nmkit - NoMachine connection launcher for desktop and demo use.

Provides a PySide6 GUI and CLI for launching NoMachine sessions from
a YAML-configured list of hosts. Designed for portable demo machines
and cross-platform remote support.

Public API:
    ConfigManager   — loads nmkit.yaml and connections.yaml
    Launcher        — generates .nxs files and launches nxclient

Exceptions:
    NmkitError          — base exception
    NmkitConfigError    — config file missing, unreadable, or invalid
    NmkitAssetError     — required font files missing and not downloaded
    NmkitLaunchError    — nxclient launch failure

CLI:
    nmkit                       # launch GUI
    nmkit connect "Name"        # launch a session by name (no GUI)
    nmkit -v                    # verbose logging
    nmkit -q                    # quiet logging
"""

from importlib.metadata import version as get_version, PackageNotFoundError

from nmkit.config import ConfigManager
from nmkit.launcher import Launcher
from nmkit.exceptions import (
    NmkitError,
    NmkitConfigError,
    NmkitAssetError,
    NmkitLaunchError,
)

try:
    __version__ = get_version("nmkit")
except PackageNotFoundError:
    __version__ = "unknown"

__author__      = "Carolyn Boyle"
__description__ = "NoMachine connection launcher for desktop and demo use"

__all__ = [
    "ConfigManager",
    "Launcher",
    "NmkitError",
    "NmkitConfigError",
    "NmkitAssetError",
    "NmkitLaunchError",
]
