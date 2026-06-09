
"""
cli.py — Command-line entry point for pack-kit.

Loads configuration, runs the pack, and optionally ships the result
to a remote host.

Usage:
    packkit
    packkit --config /path/to/packkit.yaml
    packkit --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packkit.config import load_config
from packkit.exceptions import (
    CollectorError,
    ConfigError,
    LogError,
    PackerError,
    PackkitError,
    ShipperError,
)
from packkit.logger import RunLogger
from packkit.packer import Packer
from packkit.shipper import Shipper


_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_BAD_ARGS = 2


def main() -> None:
    """Entry point — load config, run pack, ship if configured."""
    args = _parse_args()

    # --- Load config ---------------------------------------------------------
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        _error(str(exc))
        sys.exit(_EXIT_BAD_ARGS)

    logger = RunLogger(config.pack_name)

    # --- Dry run -------------------------------------------------------------
    if args.dry_run:
        _print_dry_run(config)
        sys.exit(_EXIT_OK)

    # --- Pack ----------------------------------------------------------------
    packer = Packer(config, logger)
    try:
        tarball = packer.run()
    except (CollectorError, PackerError) as exc:
        logger.log(f"FAILED: {exc}")
        try:
            logger.close(success=False)
        except LogError as log_exc:
            _error(f"Log write failed: {log_exc}")
        _error(str(exc))
        sys.exit(_EXIT_ERROR)

    # --- Ship ----------------------------------------------------------------
    if config.ship and config.ship.enabled:
        logger.log(
            f"Shipping to {config.ship.user}@{config.ship.host}:{config.ship.path}"
        )
        shipper = Shipper(config.ship)
        try:
            shipper.ship(tarball)
            logger.log("Transfer complete.")
        except ShipperError as exc:
            logger.log(f"FAILED: {exc}")
            try:
                logger.close(success=False)
            except LogError as log_exc:
                _error(f"Log write failed: {log_exc}")
            _error(str(exc))
            sys.exit(_EXIT_ERROR)

    # --- Done ----------------------------------------------------------------
    try:
        logger.close(success=True)
    except LogError as exc:
        _error(f"Log write failed: {exc}")
        sys.exit(_EXIT_ERROR)

    sys.exit(_EXIT_OK)


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """
    Build and return the parsed argument namespace.

    Returns:
        Parsed argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        prog='packkit',
        description='Pack and optionally ship server configuration archives.',
    )
    parser.add_argument(
        '--config', '-c',
        default=None,
        metavar='FILE',
        help='Path to packkit.yaml. Defaults to packkit.yaml in the current directory.',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Print what would be collected without creating an archive.',
    )
    return parser.parse_args()


def _print_dry_run(config) -> None:
    """Print a dry-run summary of what would be collected."""
    print(f"\nDry run — pack: {config.pack_name}")
    print(f"Destination:    {config.destination}\n")

    if config.files:
        print("Files:")
        for f in config.files:
            print(f"  {f}")

    if config.directories:
        print("\nDirectories:")
        for d in config.directories:
            print(f"  {d}")

    if config.commands:
        print("\nCommands:")
        for cmd in config.commands:
            print(f"  [{cmd.label}] {cmd.run}")

    if config.ship and config.ship.enabled:
        print(f"\nShip to: {config.ship.user}@{config.ship.host}:{config.ship.path}")

    print()


def _error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"packkit: error: {message}", file=sys.stderr)
