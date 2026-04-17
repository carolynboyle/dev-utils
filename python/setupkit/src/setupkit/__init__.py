"""
setupkit - Plugin installer for dev-utils / Project Crew.

Installs and updates Project Crew plugins from plugin configs stored in
~/.config/dev-utils/setupkit/. Fetches upstream manifests via
manifest.fletch, compares versions, and runs pip install as needed.

Intended for use by Quartermaster (orchestration) or directly via the
setupkit CLI.

Public API:
    init_plugin     — interactively generate a plugin config
    install_plugin  — install or update a plugin by name
    install_all     — install or update all configured plugins
    check_plugin    — check whether a plugin needs installing or updating
    check_all       — check all configured plugins
    InstallResult   — dataclass summarising the result of an install or check
    PluginConfig    — dataclass representing a validated plugin config
    ManifestData    — dataclass representing a parsed manifest.fletch
    VersionInfo     — dataclass summarising a version check result

Exceptions:
    SetupKitError       — base exception
    PluginConfigError   — plugin config missing, unreadable, or invalid
    ManifestError       — manifest.fletch fetch or parse failure
    VersionError        — version string missing or unparseable
    InstallError        — pip install subprocess failure

CLI:
    setupkit init    <n>
    setupkit install [<n>] [--force]
    setupkit check   [<n>]
"""

from importlib.metadata import version as get_version, PackageNotFoundError

from setupkit.initialize import init_plugin
from setupkit.installer import InstallResult, check_plugin, check_all, install_plugin, install_all
from setupkit.manifest import ManifestData
from setupkit.plugin import PluginConfig
from setupkit.version import VersionInfo
from setupkit.exceptions import (
    SetupKitError,
    PluginConfigError,
    ManifestError,
    VersionError,
    InstallError,
)

try:
    __version__ = get_version("setupkit")
except PackageNotFoundError:
    __version__ = "unknown"

__author__ = "Carolyn Boyle"
__description__ = "Plugin installer for dev-utils / Project Crew"

__all__ = [
    "init_plugin",
    "install_plugin",
    "install_all",
    "check_plugin",
    "check_all",
    "InstallResult",
    "PluginConfig",
    "ManifestData",
    "VersionInfo",
    "SetupKitError",
    "PluginConfigError",
    "ManifestError",
    "VersionError",
    "InstallError",
]
