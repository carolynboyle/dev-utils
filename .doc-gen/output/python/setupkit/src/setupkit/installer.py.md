# installer.py

**Path:** python/setupkit/src/setupkit/installer.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
setupkit.installer - Plugin installation orchestrator for setupkit.

Coordinates plugin.yaml loading, manifest fetching, version checking,
and pip installation. Plugin configurations are stored centrally in
~/.config/dev-utils/setupkit/<name>.yaml.

Provides both a public API for use by Quartermaster and a CLI entry
point for direct use.

Usage:
    setupkit init    <name>        — generate a plugin config interactively
    setupkit install [<name>]      — install or update one or all plugins
    setupkit check   [<name>]      — check one or all plugins
    setupkit install <name> --force — reinstall even if up to date

Public API:
    install_plugin   — install or update a plugin by name
    check_plugin     — check whether a plugin needs installing or updating
    install_all      — install or update all configured plugins
    check_all        — check all configured plugins
    InstallResult    — dataclass summarising the result of an install or check
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import argparse
from setupkit.logger import setup_logger
from setupkit.exceptions import InstallError, ManifestError, PluginConfigError, VersionError
from setupkit.manifest import fetch_manifest
from setupkit.plugin import PluginConfig, load_plugin
from setupkit.version import VersionInfo, is_update_available


from setupkit.config import ConfigManager

_config    = ConfigManager()
CONFIG_DIR = _config.config_dir


log = logging.getLogger("setupkit")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class InstallResult:
    """
    Result of a plugin install or check operation.

    Attributes:
        plugin:       The plugin name.
        action:       One of 'installed', 'updated', 'skipped', 'checked', 'failed'.
        version_info: VersionInfo from the version check, or None if unavailable.
        message:      Human-readable summary of the result.
        success:      True if the operation completed without error.
    """

    plugin: str
    action: str
    version_info: VersionInfo | None
    message: str
    success: bool


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------

def config_path(name: str) -> Path:
    """
    Return the path to a plugin's config yaml.

    Args:
        name: Plugin name (e.g. 'dbkit').

    Returns:
        Path to ~/.config/dev-utils/setupkit/<name>.yaml
    """
    return CONFIG_DIR / f"{name}.yaml"


def list_configured_plugins() -> list[str]:
    """
    Return a sorted list of all configured plugin names.

    Scans ~/.config/dev-utils/setupkit/ for .yaml files.

    Returns:
        Sorted list of plugin names (without .yaml extension).
    """
    if not CONFIG_DIR.exists():
        return []
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Public API — single plugin
# ---------------------------------------------------------------------------

def check_plugin(name: str) -> InstallResult:
    """
    Check whether a plugin needs installing or updating without making changes.

    Loads the plugin config from ~/.config/dev-utils/setupkit/<name>.yaml,
    fetches manifest.fletch, and compares versions. Does not install anything.

    Args:
        name: Plugin name (e.g. 'dbkit').

    Returns:
        An InstallResult with action='checked' and a human-readable message.

    Raises:
        PluginConfigError: If the plugin config is missing or invalid.
        ManifestError:     If manifest.fletch cannot be fetched or parsed.
        VersionError:      If version strings cannot be compared.
    """
    log.info("Checking plugin: %s", name)
    config = load_plugin(config_path(name))
    manifest = fetch_manifest(config.manifest_url)
    version_info = is_update_available(config.name, manifest.version)

    if version_info.not_installed:
        message = f"{name} is not installed (upstream: {manifest.version})"
    elif version_info.update_available:
        message = (
            f"{name} {version_info.installed} → "
            f"{version_info.upstream} (update available)"
        )
    else:
        message = f"{name} {version_info.installed} is up to date"

    log.info(message)
    return InstallResult(
        plugin=name,
        action="checked",
        version_info=version_info,
        message=message,
        success=True,
    )


def install_plugin(name: str, force: bool = False) -> InstallResult:
    """
    Install or update a plugin by name.

    Loads the plugin config from ~/.config/dev-utils/setupkit/<name>.yaml,
    fetches manifest.fletch, checks the installed version, and runs pip
    install if the plugin is missing or an update is available.
    Skips installation if already up to date, unless force=True.

    Args:
        name:  Plugin name (e.g. 'dbkit').
        force: If True, reinstall even if already up to date.

    Returns:
        An InstallResult summarising what was done.

    Raises:
        PluginConfigError: If the plugin config is missing or invalid.
        ManifestError:     If manifest.fletch cannot be fetched or parsed.
        VersionError:      If version strings cannot be compared.
        InstallError:      If the pip install subprocess fails.
    """
    log.info("Installing plugin: %s", name)
    config = load_plugin(config_path(name))
    manifest = fetch_manifest(config.manifest_url)
    version_info = is_update_available(config.name, manifest.version)

    if not force and not version_info.not_installed and not version_info.update_available:
        message = f"{name} {version_info.installed} is already up to date — skipping"
        log.info(message)
        return InstallResult(
            plugin=name,
            action="skipped",
            version_info=version_info,
            message=message,
            success=True,
        )

    action = "installed" if version_info.not_installed else "updated"
    log.info(
        "%s %s (installed: %s, upstream: %s)",
        action.capitalize(),
        name,
        version_info.installed or "none",
        version_info.upstream or "unknown",
    )

    _run_pip_install(config)

    message = f"{name} {version_info.upstream or 'unknown'} {action} successfully"
    log.info(message)
    return InstallResult(
        plugin=name,
        action=action,
        version_info=version_info,
        message=message,
        success=True,
    )


# ---------------------------------------------------------------------------
# Public API — all plugins
# ---------------------------------------------------------------------------

def check_all() -> list[InstallResult]:
    """
    Check all configured plugins for available updates.

    Scans ~/.config/dev-utils/setupkit/ and checks each plugin.
    Continues past individual failures, collecting results.

    Returns:
        List of InstallResult, one per configured plugin.
    """
    plugins = list_configured_plugins()
    if not plugins:
        log.info("No plugins configured in %s", CONFIG_DIR)
    results = []
    for name in plugins:
        try:
            results.append(check_plugin(name))
        except (PluginConfigError, ManifestError, VersionError) as exc:
            log.error("check failed for %s: %s", name, exc)
            results.append(InstallResult(
                plugin=name,
                action="failed",
                version_info=None,
                message=f"Error checking {name}: {exc}",
                success=False,
            ))
    return results


def install_all(force: bool = False) -> list[InstallResult]:
    """
    Install or update all configured plugins.

    Scans ~/.config/dev-utils/setupkit/ and installs each plugin.
    Continues past individual failures, collecting results.

    Args:
        force: If True, reinstall all plugins even if up to date.

    Returns:
        List of InstallResult, one per configured plugin.
    """
    plugins = list_configured_plugins()
    if not plugins:
        log.info("No plugins configured in %s", CONFIG_DIR)
    results = []
    for name in plugins:
        try:
            results.append(install_plugin(name, force=force))
        except (PluginConfigError, ManifestError, VersionError, InstallError) as exc:
            log.error("install failed for %s: %s", name, exc)
            results.append(InstallResult(
                plugin=name,
                action="failed",
                version_info=None,
                message=f"Error installing {name}: {exc}",
                success=False,
            ))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_pip_install(config: PluginConfig) -> None:
    """
    Run pip install for a plugin using the install URL from plugin config.

    Uses the same Python interpreter that is running setupkit to ensure
    the package is installed into the correct environment.

    Args:
        config: A validated PluginConfig instance.

    Raises:
        InstallError: If pip exits with a non-zero return code.
    """
    cmd = [sys.executable, "-m", "pip", "install", "-e", config.install.url]
    log.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        log.error("pip install failed for %s:\n%s", config.name, result.stderr)
        raise InstallError(
            f"pip install failed for {config.name} "
            f"(exit code {result.returncode}):\n{result.stderr}"
        )

    log.debug("pip output:\n%s", result.stdout)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    CLI entry point for setupkit.

    Usage:
        setupkit init    <name>
        setupkit install [<name>] [--force]
        setupkit check   [<name>]
    """
    from setupkit.initialize import init_plugin  # pylint: disable=import-outside-toplevel
    setup_logger()

    parser = argparse.ArgumentParser(
        description="Install and manage Project Crew plugins.",
        epilog="Plugin configs: ~/.config/dev-utils/setupkit/",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- init -----------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init",
        help="Generate a plugin config interactively",
    )
    init_parser.add_argument(
        "name",
        help="Plugin name (e.g. 'dbkit')",
    )

    # -- install --------------------------------------------------------------
    install_parser = subparsers.add_parser(
        "install",
        help="Install or update a plugin (omit name to install all)",
    )
    install_parser.add_argument(
        "name",
        nargs="?",
        help="Plugin name (e.g. 'dbkit'). Omit to install all configured plugins.",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall even if already up to date",
    )

    # -- check ----------------------------------------------------------------
    check_parser = subparsers.add_parser(
        "check",
        help="Check whether a plugin needs updating (omit name to check all)",
    )
    check_parser.add_argument(
        "name",
        nargs="?",
        help="Plugin name (e.g. 'dbkit'). Omit to check all configured plugins.",
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            init_plugin(args.name)

        elif args.command == "install":
            if args.name:
                result = install_plugin(args.name, force=args.force)
                print(result.message)
            else:
                results = install_all(force=args.force)
                for r in results:
                    print(r.message)

        elif args.command == "check":
            if args.name:
                result = check_plugin(args.name)
                print(result.message)
            else:
                results = check_all()
                for r in results:
                    print(r.message)

    except (PluginConfigError, ManifestError, VersionError, InstallError) as exc:
        log.error("%s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

```
