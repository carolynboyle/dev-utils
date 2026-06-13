"""
pxkit.__main__ - Entry point for pxkit.

Wires together ConfigManager, ProxmoxConnection, Launcher, and LauncherUI.
Handles CLI arguments and dispatches to the appropriate action.

Usage:
    pxkit                        # launch GUI
    pxkit -v                     # launch GUI with verbose logging
    pxkit -q                     # launch GUI with quiet logging (autostart)
    pxkit launch "Puppy Linux"   # launch VM console by name (no GUI)
    pxkit ui                     # open Proxmox web UI (no GUI)

Logging verbosity is determined in this order (highest priority first):
    1. CLI flag: -v/--verbose or -q/--quiet
    2. pxkit.yaml: log_level: verbose|normal|quiet
    3. Default: normal

Logging is initialised before anything else so all downstream
modules can log from the moment they are imported.
"""

import argparse
import logging
import sys

from pxkit.config import ConfigManager
from pxkit.connection import ProxmoxConnection
from pxkit.exceptions import PxkitError
from pxkit.launcher import Launcher
from pxkit.logger import setup_logger


def _find_vm(vms: list, name: str) -> dict:
    """
    Find a VM by name in the configured VM list.

    Args:
        vms:  List of VM dicts from ConfigManager.vms.
        name: VM name to search for (case-sensitive).

    Returns:
        Matching VM dict.

    Raises:
        SystemExit: If no VM with that name is found.
    """
    for vm in vms:
        if vm["name"] == name:
            return vm

    log = logging.getLogger("pxkit")
    available = ", ".join(f"'{v['name']}'" for v in vms)
    log.error("VM '%s' not found. Available: %s", name, available)
    print(
        f"Error: VM '{name}' not found.\nAvailable VMs: {available}",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_verbosity(args: argparse.Namespace, config: ConfigManager) -> str:
    """
    Determine log verbosity from CLI flags and config.

    CLI flags take priority over pxkit.yaml setting.

    Args:
        args:   Parsed CLI arguments.
        config: Loaded ConfigManager instance.

    Returns:
        One of 'verbose', 'normal', 'quiet'.
    """
    if args.verbose:
        return "verbose"
    if args.quiet:
        return "quiet"
    yaml_level = config.get("log_level", "normal")
    if yaml_level in ("verbose", "normal", "quiet"):
        return yaml_level
    return "normal"


def cmd_launch(args: argparse.Namespace, config: ConfigManager) -> int:
    """
    Handle the 'launch' subcommand.

    Retrieves a SPICE ticket for the named VM and launches remote-viewer.

    Args:
        args:   Parsed CLI arguments. args.vm_name is the VM name.
        config: Loaded ConfigManager instance.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    log = logging.getLogger("pxkit")
    vm  = _find_vm(config.vms, args.vm_name)

    try:
        conn       = ProxmoxConnection(config)
        launcher   = Launcher(config)
        vv_content = conn.get_spice_ticket(vm)
        launcher.launch_spice(vv_content)
        log.info("Launched VM '%s' from CLI.", args.vm_name)
        return 0
    except PxkitError as exc:
        log.error("Launch failed for VM '%s': %s", args.vm_name, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_ui(config: ConfigManager) -> int:
    """
    Handle the 'ui' subcommand.

    Opens the Proxmox web UI in the system default browser.

    Args:
        config: Loaded ConfigManager instance.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    log = logging.getLogger("pxkit")

    try:
        launcher = Launcher(config)
        launcher.open_proxmox_ui()
        log.info("Proxmox UI opened from CLI.")
        return 0
    except PxkitError as exc:
        log.error("Failed to open Proxmox UI: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_gui(config: ConfigManager) -> int:
    """
    Launch the PySide6 GUI.

    Instantiates all dependencies and starts the LauncherUI event loop.
    Importing ui here keeps PySide6 out of the import path for CLI-only
    invocations.

    Args:
        config: Loaded ConfigManager instance.

    Returns:
        Exit code (always 0 — the GUI loop runs until the user quits).
    """
    # Local import keeps PySide6 out of CLI-only execution paths.
    from pxkit.ui import LauncherUI  # pylint: disable=import-outside-toplevel

    log = logging.getLogger("pxkit")

    try:
        conn     = ProxmoxConnection(config)
        launcher = Launcher(config)
        app      = LauncherUI(config, conn, launcher)
        app.run()
        return 0
    except PxkitError as exc:
        log.error("Fatal error starting GUI: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="pxkit",
        description="Proxmox VM launcher — GUI and CLI.",
    )

    # Verbosity flags — mutually exclusive, apply to all subcommands.
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level) to file and console.",
    )
    verbosity.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress console output. Log warnings and above to file only.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # launch subcommand
    launch = subparsers.add_parser(
        "launch",
        help="Launch a VM console by name (no GUI).",
    )
    launch.add_argument(
        "vm_name",
        metavar="VM_NAME",
        help="Name of the VM to launch, as defined in pxkit.yaml.",
    )

    # ui subcommand
    subparsers.add_parser(
        "ui",
        help="Open the Proxmox web UI in the default browser (no GUI).",
    )

    return parser


def main() -> None:
    """
    pxkit entry point.

    Initialises logging, loads config, parses arguments, and dispatches
    to the appropriate command. No subcommand launches the GUI.
    """
    # Parse args first so verbosity flags are available before setup_logger.
    parser = build_parser()
    args   = parser.parse_args()

    # Bootstrap logger at normal level until config is loaded.
    setup_logger()
    log = logging.getLogger("pxkit")

    try:
        config = ConfigManager()
    except PxkitError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Re-initialise logger with resolved verbosity.
    # Clear handlers first so setup_logger() doesn't skip due to duplicate guard.
    log.handlers.clear()
    verbosity = _resolve_verbosity(args, config)
    setup_logger(verbosity=verbosity)

    log.info("pxkit starting (log level: %s).", verbosity)

    if args.command == "launch":
        sys.exit(cmd_launch(args, config))
    elif args.command == "ui":
        sys.exit(cmd_ui(config))
    else:
        sys.exit(cmd_gui(config))


if __name__ == "__main__":
    main()
