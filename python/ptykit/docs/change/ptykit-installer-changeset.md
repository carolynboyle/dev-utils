# ptykit — installer.py Changeset

**File:** `src/ptykit/installer.py`
**Status:** New file (does not exist yet)

---

## BEFORE

```python
# file does not exist
```

---

## AFTER

```python
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
```

---

## Why

**`KeyboardInterrupt` caught at top level** — Ctrl+C is normal in a
terminal game. Clean exit with a newline rather than a traceback.

**`--intercept` and `--plugins` flags on `init`** — makes
non-interactive init available from the CLI as well as from Python.
Container setup scripts can call `ptykit init advent --intercept map
--plugins ptykit_ccc.map_plugin:MapPlugin` without any prompts.

**`--config` flag** — lets containers pass an explicit config path
rather than relying on `~/.config/dev-utils/ptykit/`. The CCC
container will use this.

**No logging setup** — ptykit is a thin CLI tool, not a long-running
service. Logging to stderr on WARNING+ is sufficient without a file
handler. Add `setup_logger()` later if needed.

**`from pathlib import Path` inside the else block** — minor style
choice. Keeps the import close to where it's used since it's only
needed in the run branch.

---

## Usage examples

```bash
# Interactive config generation
ptykit init advent

# Non-interactive config generation
ptykit init advent --intercept map,hint --plugins ptykit_ccc.map_plugin:MapPlugin

# Run with default config location
ptykit --program advent

# Run with explicit config (container use)
ptykit --program advent --config /home/ccc/ptykit_ccc/data/config.yaml
```

---

## Checklist

- [ ] `src/ptykit/installer.py` written
- [ ] `pip install -e .` re-run to register the `ptykit` script
- [ ] `ptykit init advent` — walks through prompts, writes config
- [ ] `ptykit --program advent` — launches the game
- [ ] `ptykit --program advent --config /path/to/config.yaml` — works
- [ ] Ctrl+C exits cleanly with no traceback
