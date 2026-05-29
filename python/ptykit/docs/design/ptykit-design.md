# ptykit — Design Document

## What It Is

A Python package that wraps any interactive CLI program in a PTY
(pseudo-terminal), intercepts configured commands before they reach
the program, and passes everything else through transparently.

Plugins register handlers for intercepted commands and stdout lines.
ptykit is the glue layer. The intelligence lives in the plugins.

---

## Why It Exists

Any interactive CLI program can be wrapped. The immediate use cases
are Colossal Cave Adventure (CCC map plugin) and an autonomous LLM
player (smol-cave plugin), but ptykit has no knowledge of either.
It is a general-purpose tool.

---

## Structure

```
ptykit/
├── README.md
├── pyproject.toml
├── .gitignore
├── ptykit/
│   ├── __init__.py
│   ├── wrapper.py       # PTY spawn, stdout stream, stdin intercept
│   ├── plugin.py        # Base plugin class, plugin loader/registry
│   ├── context.py       # Context object passed to every plugin call
│   └── config.py        # YAML config loader
├── plugins/
│   └── README.md        # Where user/third-party plugins live
├── tests/
│   ├── __init__.py
│   ├── test_wrapper.py
│   ├── test_plugin.py
│   └── test_context.py
└── data/
    └── default_config.yaml
```

---

## Core Modules

### wrapper.py — PTYWrapper

The heart of the package. Responsibilities:

- Spawn the configured program in a PTY using `ptyprocess`
- Stream stdout to the terminal line by line
- On each stdout line, call `plugin.on_output(line, context)` for
  every registered plugin
- Read stdin character by character; buffer until newline
- On newline, check buffered input against intercept list
- If match: call `plugin.on_command(command, context)`, do NOT
  pass to program stdin
- If no match: pass buffered input to program stdin unchanged

---

### plugin.py — PtyKitPlugin (base class) + PluginRegistry

Base class all plugins inherit from:

```python
class PtyKitPlugin:
    name: str                    # unique plugin identifier

    def on_output(self, line: str, context: PtyKitContext) -> None:
        """Called for every line of stdout. Use for passive monitoring."""
        pass

    def on_command(self, command: str, context: PtyKitContext) -> None:
        """Called when an intercepted command is typed. Return value
        written to terminal if not None."""
        pass

    def on_start(self, context: PtyKitContext) -> None:
        """Called once when the wrapper starts."""
        pass

    def on_exit(self, context: PtyKitContext) -> None:
        """Called once when the wrapped program exits."""
        pass
```

PluginRegistry handles discovery and loading. Plugins are discovered
via Python entry points (`pyproject.toml`) — the standard plugin
mechanism used by pytest, flake8, and others.

---

### context.py — PtyKitContext

The object passed to every plugin method. Gives plugins access to
everything they need without coupling them to wrapper internals:

```python
class PtyKitContext:
    session_start: datetime      # when the wrapper started
    program: str                 # name of the wrapped program
    state: dict                  # plugin-local storage namespace
                                 # keyed by plugin name

    def write(self, text: str)   # write text to the terminal
    def send(self, text: str)    # send text to the program's stdin
```

`context.state[plugin.name]` gives each plugin its own isolated
storage dict. No plugin can accidentally stomp another's state.

---

### config.py — ConfigLoader

Loads and validates the YAML config file. Provides a clean config
object to the rest of the package. No other module parses YAML
directly — all config access goes through ConfigLoader.

**Responsibilities:**

- Accept a path to a YAML config file
- Load and parse the file using PyYAML
- Validate required fields (`program`, `intercept`, `plugins`)
- Provide typed accessors for each config value
- Raise clear errors on missing or malformed config

**Config structure:**

```yaml
program: advent

intercept:
  - map
  - hint
  - quit

plugins:
  - ptykit_ccc.map_plugin
  - ptykit_ccc.hint_plugin
```

**Fields:**

`program` — the CLI program to wrap. Must be on PATH or a full path.

`intercept` — list of commands to intercept. Matched
case-insensitively against the full trimmed input line. Commands not
in this list pass through to the program unchanged.

`plugins` — list of dotted module paths to plugin classes. Loaded
at startup via entry points or direct import. Order determines the
order plugins are called.

**ConfigLoader interface:**

```python
class ConfigLoader:
    def __init__(self, path: str): ...

    @property
    def program(self) -> str: ...

    @property
    def intercept(self) -> list[str]: ...

    @property
    def plugins(self) -> list[str]: ...
```

**Default config** (`data/default_config.yaml`) — shipped with the
package. Used when no config file is specified. Contains sensible
defaults with no program or plugins set — forces explicit
configuration before use.

---

## Plugin Architecture

Plugins are Python packages that depend on ptykit. They register
themselves via entry points in their own `pyproject.toml`:

```toml
[project.entry-points."ptykit.plugins"]
map = "ptykit_ccc.map_plugin:MapPlugin"
```

ptykit discovers all installed packages that register under
`ptykit.plugins` and makes them available. The YAML config selects
which ones to activate.

This means:
- ptykit has no knowledge of any specific plugin
- Any plugin installed with `pip install` is automatically
  discoverable
- Plugins are activated explicitly in the YAML config

---

## Key Decisions

**PTY library** — `ptyprocess` preferred over stdlib `pty.spawn`
because it gives finer control over the PTY file descriptor and
works more reliably across platforms. Add to dependencies.

**Entry points over directory drop** — entry points are the Python
standard. Directory scanning is fragile. Any plugin installed with
`pip install` is automatically discoverable.

**context.state keyed by plugin name** — each plugin gets isolated
storage. No shared mutable state between plugins.

**Intercept is exact match, case-insensitive** — `map`, `Map`,
`MAP` all trigger. Partial matches do not (so `mapper` passes
through to the game unchanged).

**on_output is passive** — plugins observe stdout but cannot
suppress or modify it. Output always reaches the terminal.
Suppression would break the wrapped program's display.

**Config is single source of truth** — no hardcoded defaults
in wrapper.py or plugin.py. Everything configurable comes from
the YAML file via ConfigLoader.

---

## Installation

```bash
cd dev-utils/ptykit
pip install -e .
```

## Usage

```bash
ptykit --config /path/to/config.yaml
```

---

## Status

Design complete. Not yet implemented.

**Build order:**
1. config.py + tests
2. context.py + tests
3. plugin.py (base class + registry) + tests
4. wrapper.py + tests
5. CLI entry point (`ptykit --config`)
