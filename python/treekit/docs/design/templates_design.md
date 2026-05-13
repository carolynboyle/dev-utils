# treekit: Template System Design

Created: 2026-05-11
Status: Sketch — not yet implemented

---

## Overview

Templates are markdown tree spec files stored in a well-known directory.
The `--template` flag lets treekit read from that directory by name
instead of requiring a full file path. The `--name` flag substitutes
a real project name for the placeholder in the template.

Together these two flags make treekit a spec-driven project scaffolder
that requires no editing of files before use.

---

## Template Directory

```
~/.config/dev-utils/treekit/templates/
├── python-src-layout.md     # standard src/ layout with docs, tests, data
├── python-flat.md           # flat layout (future)
└── fastapi-service.md       # FastAPI service (future)
```

Templates are plain markdown files in the same format treekit already
accepts. No new format needed.

---

## CLI Changes

### New flags

```
--template NAME, -t NAME
    Read from ~/.config/dev-utils/treekit/templates/<NAME>.md
    instead of a FILE argument. Mutually exclusive with FILE.

--name NAME, -n NAME  (note: replaces current --dry-run short flag -n)
    Substitute NAME for the placeholder package name in the template.
    Applied after parsing, before building.
```

**Note:** `-n` is currently the short flag for `--dry-run`. Needs a
decision before implementation — either reassign `-n` to `--name` and
give `--dry-run` a different short flag (e.g. `-d`), or use a different
short flag for `--name` (e.g. `-N`). Preference: `-d` for dry-run,
`-n` for name — more intuitive.

### Usage examples

```bash
# Template by name, name substitution, dry run
treekit --template python-src-layout --name myproject --dry-run

# Template by name, no substitution (uses placeholder name as-is)
treekit --template python-src-layout --output ~/projects

# File path still works as before
treekit ./docs/project-structure.md --output ~/projects
```

---

## Name Substitution

Templates use a placeholder package name. By convention: `package-name`
for the root directory and `package_name` for the Python module
(underscore form, since Python identifiers can't contain hyphens).

Example template root:
```
package-name/
├── src/
│   └── package_name/
│       ├── __init__.py
```

When `--name myproject` is passed:
- `package-name` → `myproject`
- `package_name` → `myproject` (or `my_project` if name contains hyphens)

### Implementation approach

Substitution happens on the Node tree after parsing, before building.
A `substitute_name()` function walks the tree and replaces placeholder
strings in `node.name` values.

```python
_PLACEHOLDER_HYPHEN = "package-name"
_PLACEHOLDER_UNDER  = "package_name"

def substitute_name(root: Node, name: str) -> Node:
    """
    Replace placeholder package name in all Node names.

    Args:
        root: Root Node of the parsed tree.
        name: Actual project name to substitute.

    Returns:
        The same tree with names substituted in place.
    """
    under = name.replace("-", "_")
    _substitute_node(root, name, under)
    return root

def _substitute_node(node: Node, hyphen: str, under: str) -> None:
    node.name = (
        node.name
        .replace(_PLACEHOLDER_HYPHEN, hyphen)
        .replace(_PLACEHOLDER_UNDER, under)
    )
    for child in node.children:
        _substitute_node(child, hyphen, under)
```

This keeps substitution out of `TreeParser` and `TreeBuilder` — neither
needs to know about templates. Substitution is a thin layer in `cli.py`
between parse and build.

---

## Template Resolution

`TemplateResolver` — new module `resolver.py`:

```python
class TemplateResolver:
    def __init__(self, template_dir: Path | None = None):
        self._dir = template_dir or _DEFAULT_TEMPLATE_DIR

    def resolve(self, name: str) -> Path:
        """
        Return the path to a named template file.

        Raises:
            TemplateNotFoundError if the template does not exist.
        """
        path = self._dir / f"{name}.md"
        if not path.exists():
            raise TemplateNotFoundError(
                f"Template {name!r} not found in {self._dir}"
            )
        return path

    def list_templates(self) -> list[str]:
        """Return names of all available templates."""
        if not self._dir.exists():
            return []
        return sorted(p.stem for p in self._dir.glob("*.md"))
```

---

## Exception Additions

Two new exceptions in `exceptions.py`:

```python
class TemplateError(TreekitError):
    """Base class for template exceptions."""

class TemplateNotFoundError(TemplateError):
    """Raised when a named template cannot be found in the template directory."""
```

---

## New `--list-templates` flag

```bash
treekit --list-templates
```

Prints available templates from the template directory. Useful for
discoverability on a new machine.

---

## Module changes summary

| Module | Change |
|---|---|
| `cli.py` | Add `--template`, `--name`, `--list-templates` flags; wire substitution |
| `exceptions.py` | Add `TemplateError`, `TemplateNotFoundError` |
| `__init__.py` | Export new exceptions and `TemplateResolver` |
| `resolver.py` | New — `TemplateResolver` class |
| `substitution.py` | New — `substitute_name()` function |

`node.py`, `parser.py`, `builder.py` — **no changes needed.**

---

## Tests needed

- `test_resolver.py` — resolve by name, list templates, missing template error
- `test_substitution.py` — hyphen/underscore substitution, nested nodes,
  names with no placeholder (no-op), names containing hyphens
- `test_cli.py` additions — `--template` flag, `--name` flag,
  `--list-templates` output, mutual exclusion of FILE and `--template`

---

## Open questions

1. Should `--name` be required when `--template` is used, or optional
   (defaulting to the placeholder name)? Optional is more forgiving;
   required prevents accidentally creating `package-name/` directories.
   Preference: optional with a warning if placeholder name is detected
   in the output path.

2. Should templates be version-controlled in the dev-utils repo and
   copied to `~/.config/dev-utils/treekit/templates/` by setupkit on
   install, or managed entirely as local files? Version-controlled is
   better for consistency across machines.

3. The `-n` / `--dry-run` short flag conflict needs resolving before
   implementation begins.

---

## Related

- `treekit/README.md` — current treekit documentation
- `treekit-in-projs.md` — projs integration design
- `python-src-layout.md` — the first template (to be written)
