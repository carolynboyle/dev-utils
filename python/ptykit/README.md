# ptykit

PTY wrapper with plugin-based command interception.

Wraps any interactive CLI program in a pseudo-terminal, intercepts
configured commands before they reach the program, and dispatches to
registered plugins. Everything else passes through transparently.

Part of [dev-utils](https://github.com/carolynboyle/dev-utils).

---

## What it does

```
user types "map" → ptykit intercepts → MapPlugin renders visited rooms
user types "north" → passes through to the program unchanged
program prints output → plugins observe it → user sees it
```

ptykit is the plumbing. The intelligence lives in the plugins.

---

## Install

```bash
cd ~/projects/dev-utils/python/ptykit
pip install -e .
```

---

## Quick start

Generate a config for the program you want to wrap:

```bash
ptykit init advent
```

This creates `~/.config/dev-utils/ptykit/advent.yaml`. Edit it or
let `init` walk you through it interactively.

Then run:

```bash
ptykit --program advent
```

---

## Config

`~/.config/dev-utils/ptykit/<program>.yaml`

```yaml
program: advent

intercept:
  - map
  - hint

plugins:
  - ptykit_ccc.map_plugin:MapPlugin
```

`program` — the CLI program to wrap. Must be on PATH.

`intercept` — commands typed by the user that ptykit handles instead
of passing to the program. Case-insensitive.

`plugins` — dotted paths to plugin classes. Loaded at startup.

---

## Writing a plugin

```python
from ptykit.plugin import PtyKitPlugin

class MapPlugin(PtyKitPlugin):
    name = "map_plugin"

    def on_start(self, context):
        context.state[self.name] = {"rooms": []}

    def on_output(self, line, context):
        if "You are" in line:
            context.state[self.name]["rooms"].append(line)

    def on_command(self, command, context):
        rooms = context.state[self.name]["rooms"]
        context.write("\n".join(rooms) + "\n")
```

Register your plugin via entry points in your `pyproject.toml`:

```toml
[project.entry-points."ptykit.plugins"]
map = "ptykit_ccc.map_plugin:MapPlugin"
```

### Plugin hooks

| Hook | When called | Use for |
|---|---|---|
| `on_start` | Once at startup | Initialise state |
| `on_output` | Every stdout line | Detect events, track state |
| `on_command` | Intercepted command typed | Render output, inject input |
| `on_exit` | Program exits | Flush state, clean up |

### Context

Every hook receives a `PtyKitContext`:

```python
context.program        # name of the wrapped program
context.session_start  # datetime the wrapper started
context.state          # dict keyed by plugin name — your storage
context.write(text)    # write to the terminal
context.send(text)     # send to the program's stdin
```

---

## Non-interactive config generation

For container setup scripts or automation:

```python
from ptykit.initialize import init_config

init_config(
    program="advent",
    intercept=["map", "hint"],
    plugins=["ptykit_ccc.map_plugin:MapPlugin"],
)
```

No prompts. Config written to
`~/.config/dev-utils/ptykit/advent.yaml`.

---

## Known plugins

| Plugin | Wraps | What it adds |
|---|---|---|
| [ptykit-ccc](../../games_in_a_can/ccc) | Colossal Cave Adventure | Visited rooms map |

---

## License

GNU General Public License v3.0 or later. See `LICENSE`.

**tl;dr** — Use it, modify it, build on it. Just keep it open source.
If you distribute software that includes ptykit, your code must be
open source too. That's the deal.