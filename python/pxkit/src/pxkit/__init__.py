"""
pxkit - Proxmox VM launcher for desktop and demo use.

Provides a tkinter GUI and CLI for launching Proxmox VM consoles
and opening the Proxmox web UI. Designed for portable demo machines
and small business server solutions.

Public API:
    ConfigManager       — loads and merges pxkit YAML configuration
    ProxmoxConnection   — Proxmox API calls and SPICE ticket retrieval
    Launcher            — opens Proxmox web UI and launches VM consoles

Exceptions:
    PxkitError          — base exception
    PxkitConfigError    — config file missing, unreadable, or invalid
    PxkitConnectionError — Proxmox API call failure
    PxkitLaunchError    — browser or remote-viewer launch failure

CLI:
    pxkit                        # launch GUI
    pxkit launch "VM Name"       # launch VM console by name
    pxkit ui                     # open Proxmox web UI
"""

from importlib.metadata import version as get_version, PackageNotFoundError

from pxkit.config import ConfigManager
from pxkit.connection import ProxmoxConnection
from pxkit.launcher import Launcher
from pxkit.exceptions import (
    PxkitError,
    PxkitConfigError,
    PxkitConnectionError,
    PxkitLaunchError,
)

try:
    __version__ = get_version("pxkit")
except PackageNotFoundError:
    __version__ = "unknown"

__author__ = "Carolyn Boyle"
__description__ = "Proxmox VM launcher for desktop and demo use"

__all__ = [
    "ConfigManager",
    "ProxmoxConnection",
    "Launcher",
    "PxkitError",
    "PxkitConfigError",
    "PxkitConnectionError",
    "PxkitLaunchError",
]
