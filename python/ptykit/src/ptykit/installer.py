"""
ptykit/installer.py

CLI entry point for ptykit.

Dispatches to initialize.init_config() for config generation,
or assembles and runs PTYWrapper for a named program.

Usage:
    ptykit init <program>
    ptykit --program <program>
    ptykit --program <program> --config /path/to/config.yaml
"""

import argparse
import logging
import sys

from ptykit.config import ConfigLoader
from ptykit.context import PtyKitContext
from ptykit.exceptions import PtyKitConfigError, PtyKitPluginError, PtyKitWrapperError
from ptykit.initialize import init_config
from ptykit.plugin import PluginRegistry
from ptykit.wrapper import PTYWrapper

log = logging.getLogger("ptykit")


def main() -> None:
    """
    CLI entry point for ptykit.

    Subcommands:
        init <program>   — generate a config interactively
        run (default)    — wrap a program using its config

    Flags:
        --program        — program name to wrap
        --config         — explicit path to config file (optional)
    """
    parser = argparse.ArgumentParser(
        description="PTY wrapper with plugin-based command interception.",
        epilog="Configs: ~/.config/dev-utils/ptykit/<program>.yaml",
    )

    subparsers = parser.add_subparsers(dest="command")

    # -- init -----------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init",
        help="Generate a ptykit config interactively",
    )
    init_parser.add_argument(
        "program",
        help="Program name (e.g. 'advent')",
    )
    init_parser.add_argument(
        "--intercept",
        help="Comma-separated commands to intercept (skips prompt)",
    )
    init_parser.add_argument(
        "--plugins",
        help="Comma-separated plugin paths (skips prompt)",
    )

    # -- run (default) --------------------------------------------------------
    parser.add_argument(
        "--program",
        help="Program to wrap (e.g. 'advent')",
    )
    parser.add_argument(
        "--config",
        help="Explicit path to config yaml (optional)",
    )

    args = parser.parse_args()

    # -- Dispatch -------------------------------------------------------------
    try:
        if args.command == "init":
            intercept = (
                [c.strip() for c in args.intercept.split(",")]
                if args.intercept else None
            )
            plugins = (
                [p.strip() for p in args.plugins.split(",")]
                if args.plugins else None
            )
            init_config(
                program=args.program,
                intercept=intercept,
                plugins=plugins,
            )

        else:
            if not args.program:
                parser.print_help()
                sys.exit(1)

            from pathlib import Path
            config_file = Path(args.config) if args.config else None
            config = ConfigLoader(args.program, config_file=config_file)
            registry = PluginRegistry(config.plugins)
            wrapper = PTYWrapper(config, registry)
            wrapper.run()

    except PtyKitConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)
    except PtyKitPluginError as exc:
        print(f"Plugin error: {exc}", file=sys.stderr)
        sys.exit(1)
    except PtyKitWrapperError as exc:
        print(f"Wrapper error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
