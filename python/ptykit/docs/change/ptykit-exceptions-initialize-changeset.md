# ptykit — exceptions.py + initialize.py Changesets

---

## File 1: `ptykit/exceptions.py`

**Status:** New file (empty → implemented)

Must exist before config.py, initialize.py, or any other module.

### BEFORE

```python
# empty
```

### AFTER

```python
"""
ptykit/exceptions.py

Exception hierarchy for ptykit.

All ptykit exceptions inherit from PtyKitError so callers can catch
the base class if they don't need to distinguish specific failures.

Exception hierarchy:
    PtyKitError
    ├── PtyKitConfigError   — config file missing, unreadable, or invalid
    ├── PtyKitPluginError   — plugin load or registration failure
    └── PtyKitWrapperError  — PTY spawn or IO failure
"""


class PtyKitError(Exception):
    """Base exception for all ptykit errors."""


class PtyKitConfigError(PtyKitError):
    """
    Raised when a config file is missing, unreadable, or fails validation.
    """


class PtyKitPluginError(PtyKitError):
    """
    Raised when a plugin cannot be loaded or registered.
    """


class PtyKitWrapperError(PtyKitError):
    """
    Raised when the PTY wrapper fails to spawn or communicate
    with the wrapped program.
    """
```

### Why

Mirrors setupkit's exception hierarchy exactly. Named exceptions make
it easy for callers to catch specific failure modes. All inherit from
`PtyKitError` so callers can catch the base class when they don't
need to distinguish.

---

## File 2: `ptykit/initialize.py`

**Status:** New file (empty → implemented)

### BEFORE

```python
# empty
```

### AFTER

```python
"""
ptykit/initialize.py

Config generator for ptykit.

Generates a program config yaml in
~/.config/dev-utils/ptykit/<program>.yaml.

Can be called non-interactively by supplying all parameters — useful
for container setup scripts. Falls back to interactive prompts for
any parameter not supplied.

Workflow:
    1. Accept program name + optional intercept list + optional plugins list
    2. Prompt for any missing values
    3. If config already exists, show diff and confirm overwrite
    4. Write ~/.config/dev-utils/ptykit/<program>.yaml

Public API:
    init_config — generate a ptykit config for a named program

CLI:
    ptykit init <program>
"""

import sys
from pathlib import Path

import yaml

from ptykit.config import config_path
from ptykit.exceptions import PtyKitConfigError


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_config(
    program: str,
    intercept: list[str] | None = None,
    plugins: list[str] | None = None,
) -> Path:
    """
    Generate a ptykit config for a named program.

    If intercept or plugins are not supplied, prompts interactively.
    If all are supplied, writes the config without any prompts — safe
    to call from container setup scripts or other automation.

    Args:
        program:   The CLI program to wrap (e.g. 'advent').
        intercept: List of commands to intercept (e.g. ['map', 'hint']).
                   If None, prompts interactively.
        plugins:   List of plugin dotted paths
                   (e.g. ['ptykit_ccc.map_plugin:MapPlugin']).
                   If None, prompts interactively.

    Returns:
        Path to the written config file.

    Raises:
        PtyKitConfigError: If the config file cannot be written.
    """
    print(f"\nptykit init — configuring: {program}")
    print("=" * 50)

    if intercept is None:
        intercept = _prompt_intercept()

    if plugins is None:
        plugins = _prompt_plugins()

    config = {
        "program": program,
        "intercept": intercept,
        "plugins": plugins,
    }

    dest = config_path(program)

    if dest.exists():
        _confirm_overwrite(dest, config)

    _write_config(dest, config)
    return dest


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _prompt_intercept() -> list[str]:
    """
    Prompt for the list of commands to intercept.

    Returns:
        List of lowercase command strings.
    """
    print("\nCommands to intercept (comma-separated).")
    print("These are typed by the player but handled by ptykit,")
    print("not passed to the wrapped program.")
    print("Example: map, hint, help")

    while True:
        raw = input("\nIntercept commands: ").strip()
        if raw:
            return [c.strip().lower() for c in raw.split(",") if c.strip()]
        print("At least one command required.")


def _prompt_plugins() -> list[str]:
    """
    Prompt for the list of plugins to activate.

    Returns:
        List of dotted plugin path strings.
    """
    print("\nPlugins to activate (comma-separated dotted paths).")
    print("Example: ptykit_ccc.map_plugin:MapPlugin")
    print("Leave blank for no plugins.")

    raw = input("\nPlugins: ").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _confirm_overwrite(dest: Path, new_config: dict) -> None:
    """
    Show existing and new config, prompt to confirm overwrite.

    Args:
        dest:       Path to the existing config file.
        new_config: The new config dict to be written.
    """
    print(f"\nConfig already exists: {dest}")
    print("\nExisting config:")
    print(dest.read_text(encoding="utf-8"))
    print("New config:")
    print(yaml.dump(new_config, default_flow_style=False, sort_keys=False))

    answer = input("Overwrite existing config? [y/N]: ").strip().lower()
    if answer != "y":
        print("Aborted. Existing config unchanged.")
        sys.exit(0)


def _write_config(dest: Path, config: dict) -> None:
    """
    Write a config dict to disk as YAML.

    Args:
        dest:   Destination path for the config file.
        config: Config dict to serialise.

    Raises:
        PtyKitConfigError: If the file cannot be written.
    """
    header = (
        f"# ptykit config — generated by ptykit init\n"
        f"# Edit manually or regenerate with: "
        f"ptykit init {config['program']}\n\n"
    )
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            header + yaml.dump(
                config, default_flow_style=False, sort_keys=False
            ),
            encoding="utf-8",
        )
        print(f"\nWritten: {dest}")
        print(f"Run with: ptykit --program {config['program']}")
    except OSError as exc:
        raise PtyKitConfigError(
            f"Could not write config {dest}: {exc}"
        ) from exc
```

### Why

**`intercept` and `plugins` default to `None`** — not empty lists.
`None` means "not supplied, prompt for it." An empty list is a valid
supplied value (no intercepts, no plugins). The distinction matters
for non-interactive use.

**Returns `Path`** — calling scripts can log or verify where the
config landed without re-deriving the path themselves.

**No registry, no manifest** — ptykit configs are simple. There is
nothing to fetch. The interactive path is just two prompts.

**`_confirm_overwrite` and `_write_config`** — copied from setupkit's
pattern verbatim. Consistent UX across all dev-utils tools.

**`sys.exit(0)` on abort** — same as setupkit. Clean exit, not an
exception, when the user chooses not to overwrite.

---

## Non-interactive usage example

From a container setup script:

```python
from ptykit.initialize import init_config

init_config(
    program="advent",
    intercept=["map", "hint"],
    plugins=["ptykit_ccc.map_plugin:MapPlugin"],
)
```

No prompts. Config written to
`~/.config/dev-utils/ptykit/advent.yaml` and the path returned.

---

## Interactive usage

```
$ ptykit init advent

ptykit init — configuring: advent
==================================================

Commands to intercept (comma-separated).
These are typed by the player but handled by ptykit,
not passed to the wrapped program.
Example: map, hint, help

Intercept commands: map

Plugins to activate (comma-separated dotted paths).
Example: ptykit_ccc.map_plugin:MapPlugin
Leave blank for no plugins.

Plugins: ptykit_ccc.map_plugin:MapPlugin

Written: /home/carolyn/.config/dev-utils/ptykit/advent.yaml
Run with: ptykit --program advent
```

---

## Checklist

- [ ] `ptykit/exceptions.py` written
- [ ] `ptykit/initialize.py` written
- [ ] `ptykit/config.py` written (depends on exceptions)
- [ ] `pytest tests/test_config.py` passes
- [ ] Manual test: `ptykit init advent` → check file written
- [ ] Manual test: call `init_config("advent", intercept=["map"], plugins=[])` → no prompts
