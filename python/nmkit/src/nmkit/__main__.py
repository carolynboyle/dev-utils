"""
nmkit.__main__ - Entry point for nmkit.

Wires together assets, ConfigManager, Launcher, and LauncherUI.
Handles CLI arguments, logging, and startup asset checks.

Usage:
    nmkit                       # launch GUI (default)
    nmkit connect "Rocky"       # launch a session by name (no GUI)
    nmkit -v                    # verbose logging
    nmkit -q                    # quiet logging

Logging is initialised before anything else so all downstream
modules can log from the moment they are imported.

Asset check (Font Awesome fonts) runs before the Qt application
is created, since it uses stdin for user prompts.
"""

import argparse
import logging
import sys

from nmkit.assets import check as assets_check
from nmkit.config import ConfigManager
from nmkit.exceptions import NmkitAssetError, NmkitError
from nmkit.logger import setup_logger


def _find_connection(connections: list, name: str) -> dict:
    """
    Find a connection by name in the configured connection list.

    Args:
        connections: List of connection dicts from ConfigManager.connections.
        name:        Connection name to search for (case-sensitive).

    Returns:
        Matching connection dict.

    Raises:
        SystemExit: If no connection with that name is found.
    """
    for conn in connections:
        if conn["name"] == name:
            return conn

    log       = logging.getLogger("nmkit")
    available = ", ".join(f"'{c['name']}'" for c in connections)
    log.error("Connection '%s' not found. Available: %s", name, available)
    print(
        f"Error: Connection '{name}' not found.\n"
        f"Available connections: {available}",
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_connect(args: argparse.Namespace, config: ConfigManager) -> int:
    """
    Handle the 'connect' subcommand.

    Launches an nxclient session for the named connection without
    opening the GUI.

    Args:
        args:   Parsed CLI arguments. args.name is the connection name.
        config: Loaded ConfigManager instance.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    from nmkit.launcher import Launcher  # pylint: disable=import-outside-toplevel

    log  = logging.getLogger("nmkit")
    conn = _find_connection(config.connections, args.name)

    try:
        launcher = Launcher(config)
        launcher.launch(conn)
        log.info("Launched connection '%s' from CLI.", args.name)
        return 0
    except NmkitError as exc:
        log.error("Launch failed for '%s': %s", args.name, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_gui(config: ConfigManager) -> int:
    """
    Launch the PySide6 GUI.

    Instantiates all dependencies and starts the LauncherUI event loop.
    Fonts are loaded after QApplication is created (Qt requirement).

    Args:
        config: Loaded ConfigManager instance.

    Returns:
        Exit code from QApplication.exec().
    """
    # Local imports keep PySide6 out of CLI-only execution paths.
    from nmkit.icons import load_fonts       # pylint: disable=import-outside-toplevel
    from nmkit.launcher import Launcher      # pylint: disable=import-outside-toplevel
    from nmkit.ui import LauncherUI          # pylint: disable=import-outside-toplevel

    log = logging.getLogger("nmkit")

    try:
        launcher = Launcher(config)
        app      = LauncherUI(config, launcher)
        # load_fonts() must be called after QApplication exists (created
        # inside LauncherUI.__init__) and after assets_check() confirms
        # the .ttf files are present.
        load_fonts()
        return app.run()
    except NmkitError as exc:
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
        prog="nmkit",
        description="NoMachine connection launcher — GUI and CLI.",
    )

    # Logging verbosity flags (mutually exclusive).
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    verbosity.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all console output.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # connect subcommand
    connect = subparsers.add_parser(
        "connect",
        help="Launch a NoMachine session by name (no GUI).",
    )
    connect.add_argument(
        "name",
        metavar="NAME",
        help="Connection name as defined in connections.yaml.",
    )

    return parser


def main() -> None:
    """
    nmkit entry point.

    1. Initialises logging.
    2. Runs the asset check (font file presence, with download prompt).
    3. Loads configuration.
    4. Parses CLI arguments.
    5. Dispatches to connect subcommand or GUI.
    """
    # Logging first — everything downstream can log from here.
    setup_logger()
    log = logging.getLogger("nmkit")
    log.info("nmkit starting.")

    # Asset check before Qt — uses stdin for user prompts.
    try:
        assets_check()
    except NmkitAssetError as exc:
        print(f"Asset error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Configuration.
    try:
        config = ConfigManager()
    except NmkitError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    # CLI arguments.
    parser = build_parser()
    args   = parser.parse_args()

    # Apply verbosity override from CLI flags.
    if args.verbose:
        logging.getLogger("nmkit").setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger("nmkit").setLevel(logging.CRITICAL)

    # Dispatch.
    if args.command == "connect":
        sys.exit(cmd_connect(args, config))
    else:
        # No subcommand — launch GUI.
        sys.exit(cmd_gui(config))


if __name__ == "__main__":
    main()
