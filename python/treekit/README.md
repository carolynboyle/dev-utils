# treekit

Directory tree scaffolding tool for the dev-utils toolkit / Project Crew.

Reads a markdown file containing a directory tree structure and creates the
corresponding empty files and directories on disk. Supports fenced code blocks
and bare tree text. Works as a standalone CLI or as a library.

---

## Installation

### Via setupkit (recommended)

```bash
setupkit install treekit
```

### From dev-utils repo (development mode)

```bash
cd ~/projects/dev-utils/python/treekit
pip install -e .
```

Verify:

```bash
treekit --help
```

---

## Quick Start

Write a markdown file describing your project structure:

````markdown
```
my_project/
├── src/
│   └── my_project/
│       ├── __init__.py
│       └── core.py        # Core module
├── tests/
│   └── test_core.py
└── pyproject.toml
```
````

Create the structure:

```bash
treekit my_project.md
```

Preview first with dry run:

```bash
treekit my_project.md --dry-run
```

Create under a specific directory:

```bash
treekit my_project.md --output ~/projects
```

Pipe from stdin:

```bash
cat my_project.md | treekit --output ~/projects
```

---

## Input Format

treekit accepts two input formats.

### Fenced code block

Tree content inside triple backticks (``` ``` ```) or tildes (`~~~`):

````markdown
```
project/
├── src/
│   └── main.py
└── README.md
```
````

### Bare tree text

Tree content without fencing — the entire file is treated as a tree:

```
project/
├── src/
│   └── main.py
└── README.md
```

### Inline comments

Comments after `#` are stripped before creating paths and stored as metadata.
They appear in dry-run output and the run log but are never written to disk:

```
project/
├── src/               # Source package
│   └── main.py        # Entry point
└── README.md
```

### Rules

- The first entry must be a directory (trailing `/`) — this becomes the root.
- Directories have a trailing `/`; files do not.
- Standard tree drawing characters (`├──`, `└──`, `│`) are recognised and stripped.
- Blank lines are ignored.

---

## Options

| Option | Short | Description |
|---|---|---|
| `FILE` | | Markdown file to read. Reads from stdin if omitted. |
| `--output DIR` | `-o` | Directory to create the tree under. Defaults to current directory. |
| `--dry-run` | `-n` | Preview what would be created, then prompt for confirmation. |

---

## Dry Run

Dry run prints the full list of paths that would be created, then prompts
for confirmation before proceeding:

```
Dry run — output: /home/carolyn/projects

Would create:
  my_project/
  my_project/src/
  my_project/src/my_project/
  my_project/src/my_project/__init__.py
  my_project/src/my_project/core.py
  my_project/tests/
  my_project/tests/test_core.py
  my_project/pyproject.toml

Create this structure? [y/N]
```

Enter `y` to proceed, anything else to abort. Aborting exits with code 0 —
no harm done.

---

## Existing Paths

treekit never overwrites existing files or destroys existing directories.

- **Existing directory** where a directory is expected: skipped, children still processed.
- **Existing file** where a file is expected: skipped, contents untouched.
- **File where a directory is expected** (or vice versa): recorded as an error, reported in summary and log.

---

## Logging

Every run — dry or live — appends a plain-text entry to:

```
~/.config/dev-utils/treekit/treekit.log
```

Example entry:

```
=== 2026-05-11 14:32:07 ===
Source:   my_project.md
Output:   /home/carolyn/projects
Dry-run:  no

CREATED:
  my_project/
  my_project/src/
  my_project/src/my_project/
  my_project/src/my_project/__init__.py
  my_project/src/my_project/core.py
  my_project/tests/
  my_project/tests/test_core.py
  my_project/pyproject.toml

===
```

A log write failure is reported as a warning but does not abort a successful build.

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success, or dry run aborted by user. |
| `1` | Parse or build error. |
| `2` | Bad arguments (e.g. no input and stdin is a terminal). |

---

## As a Library

Import treekit for use in other tools:

```python
from pathlib import Path
from treekit import TreeParser, TreeBuilder

parser = TreeParser()
root = parser.parse(Path('my_project.md').read_text(encoding='utf-8'))

builder = TreeBuilder(output_path=Path('/home/carolyn/projects'), dry_run=False)
result = builder.build(root)

print(f"Created: {len(result.created)}")
print(f"Skipped: {len(result.skipped)}")
print(f"Errors:  {len(result.errors)}")
```

### Public API

**`TreeParser`**
- `parse(text: str) -> Node` — parse markdown text into a Node tree.

**`TreeBuilder(output_path, dry_run, source)`**
- `build(root: Node) -> BuildResult` — create the filesystem tree.

**`Node`**
- `name: str` — filename or directory name, no path component.
- `is_dir: bool` — True for directories.
- `depth: int` — zero-based nesting depth.
- `children: list[Node]` — direct children.
- `comment: Optional[str]` — inline comment, if present.

**`BuildResult`**
- `created: list[str]` — paths created (or would-be-created in dry run).
- `skipped: list[str]` — paths that already existed.
- `errors: list[tuple[str, str]]` — (path, message) pairs for failures.
- `success: bool` — True when errors is empty.

### Exceptions

| Exception | Cause |
|---|---|
| `TreekitError` | Base class for all treekit exceptions. |
| `ParseError` | Base class for parser exceptions. |
| `EmptyInputError` | Input is empty or whitespace only. |
| `NoTreeFoundError` | Input contains no recognisable tree structure. |
| `BuildError` | Base class for builder exceptions. |
| `OutputPathError` | Output path missing or not a directory. |
| `PathCollisionError` | Type mismatch between expected and existing path. |
| `TkPermissionError` | Permission denied during filesystem operation. |
| `LogError` | Log write failed. |

---

## On the Horizon

A companion feature is planned that does the inverse: point treekit at an
existing project directory and export its structure as treekit-compatible
markdown. Dr. Filewalker already walks the filesystem; the companion will
be a thin renderer over his output.

---

## Dependencies

- Python 3.11+
- No third-party dependencies.

---

## Development

### Install in dev mode

```bash
cd ~/projects/dev-utils/python/treekit
pip install -e .
```

### Run tests

```bash
pytest tests/
```

### Lint

```bash
pylint src/treekit
```

### Code style

Follows Project Crew design rules:
- One class or cohesive set of functions per module.
- No hard-coded values.
- Explicit exception handling — no bare `except`.
- 120-character line limit.
- `encoding='utf-8'` on all file I/O.

---

## License

MIT License. See `LICENSE` file in this directory.

---

## Part of Project Crew

treekit is one tool in the Project Crew ecosystem:

- **doc-gen** — filesystem manifest generator; Dr. Filewalker 🩺
- **fletcher** — GitHub URL manifest generator
- **treekit** — directory tree scaffolding from markdown
- **setupkit** — plugin lifecycle manager
- **menukit** — YAML-driven menu library
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **viewkit** — YAML-driven SQL query and view builder
- **todo** — task manager with JSON storage
- **projs** — project launcher and management CLI

All tools follow the same design principles and can work together or standalone.

---

## Contributing

Contributions welcome. Please read `PROJECT_RULES.md` in the dev-utils repo
before submitting.

---

## Author

Carolyn Boyle

---

## Changelog

### 0.1.0 (2026-05-11)

- Initial release
- Fenced code block and bare tree input
- Inline comment stripping and storage
- Dry-run mode with confirmation prompt
- Skip existing files and directories cleanly
- Plain-text run log at `~/.config/dev-utils/treekit/treekit.log`
- Full exception hierarchy
- Usable as a library
