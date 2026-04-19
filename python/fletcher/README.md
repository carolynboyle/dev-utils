# fletcher

Raw GitHub URL manifest generator for the dev-utils toolkit / Project Crew.

Reads a Dr. Filewalker project manifest and generates a `.fletch` YAML file with GitHub URLs for all project files — suitable for sharing with AI assistants or using in downstream automation.

## Installation

### From dev-utils repo (development mode)

```bash
python3.11 -m venv /opt/venvs/tools/fletcher
/opt/venvs/tools/fletcher/bin/pip install -e ~/projects/dev-utils/python/fletcher
sudo ln -s /opt/venvs/tools/fletcher/bin/fletcher /usr/local/bin/fletcher
```

Verify:
```bash
fletcher --help
```

### From PyPI (when published)

```bash
pip install fletcher
```

---

## Quick Start

### Basic usage (interactive)

From inside any project directory with a `.doc-gen/manifest.yml`:

```bash
fletcher
```

This will:
1. Detect your git remote origin
2. Detect your current branch
3. Prompt you to confirm (or select from saved repos)
4. Generate `manifest.fletch` in the same directory as your manifest

### With options

```bash
# Specify branch explicitly
fletcher --branch develop

# Use a specific repo (skips menu)
fletcher --repo https://github.com/carolynboyle/projs

# Generate web URLs (human-readable) instead of raw URLs
fletcher --web

# Save output to custom location
fletcher --output ~/Desktop/project-urls.fletch

# Combine options
fletcher --repo https://github.com/carolynboyle/fletcher --branch main --web --output urls.fletch
```

---

## What It Does

### Input

Reads a **Dr. Filewalker manifest** at `.doc-gen/manifest.yml`:

```yaml
documents:
  - path: src/main.py
    description: Entry point
  - path: src/core/engine.py
    description: Core logic
  - path: README.md
    description: Documentation
```

### Output

Generates a `.fletch` manifest with GitHub URLs:

```yaml
# Generated: 2025-04-18 14:32:15
# Repo: https://github.com/carolynboyle/fletcher
# Branch: main
# URL type: raw
# Version: 0.1.0
# Files: 3

repo: https://github.com/carolynboyle/fletcher
branch: main
url_type: raw
generated: 2025-04-18 14:32:15
version: 0.1.0
files:
  - path: src/main.py
    url: https://raw.githubusercontent.com/carolynboyle/fletcher/main/src/main.py
  - path: src/core/engine.py
    url: https://raw.githubusercontent.com/carolynboyle/fletcher/main/src/core/engine.py
  - path: README.md
    url: https://raw.githubusercontent.com/carolynboyle/fletcher/main/README.md
```

### Use Case

Upload the `.fletch` file to an AI assistant in a single turn, then the assistant can:

```
I've attached fletcher.fletch. Use the URLs inside to fetch all project files.
```

The assistant reads the manifest and retrieves all files — no need for multiple uploads, connectors, or manual file sharing.

---

## Configuration

### Optional: Save preferences in `~/.config/dev-utils/config.yaml`

```yaml
fletcher:
  repos:
    - https://github.com/carolynboyle/projs
    - https://github.com/carolynboyle/fletcher
    - https://github.com/carolynboyle/doc-gen
  branch: main
  url_type: raw
```

**Options:**
- `repos` — list of GitHub URLs you work with (displayed in menu, most recent first)
- `branch` — default branch if not specified via CLI (overridden by `--branch` flag)
- `url_type` — `raw` (default) for raw.githubusercontent.com URLs, `web` for github.com/blob URLs

**Priority (highest to lowest):**
1. `--branch` CLI flag
2. `fletcher.branch` from config
3. Auto-detected from git (via `git rev-parse --abbrev-ref HEAD`)

---

## Branch Detection

fletcher automatically detects your current branch:

```bash
# Inside a git repo on 'develop' branch
fletcher
# Automatically uses 'develop' (unless you override with --branch)
```

If branch detection fails:
- **Not a git repository** → error message tells you to run fletcher from a git repo
- **No commits yet (empty HEAD)** → error message tells you to make an initial commit first
- **git not installed** → error message tells you to install git

No silent fallbacks. Always explicit.

---

## Logging

fletcher logs to two files in `~/.local/share/dev-utils/`:

- `fletcher.log` — human-readable, INFO+ level
- `fletcher.json.log` — JSON lines (one object per log event)

Use logs to debug issues or audit manifest generation.

---

## As a Library

Import fletcher functions for use in other tools:

```python
from fletcher import build_url_manifest, write_manifest

# Generate manifest programmatically
paths = ["src/main.py", "README.md"]
repo = "https://github.com/carolynboyle/fletcher"
branch = "main"
url_type = "raw"

manifest = build_url_manifest(paths, repo, branch, url_type)
write_manifest(manifest, Path("output.fletch"))
```

Public API:
- `build_url_manifest(paths, repo, branch, url_type) -> dict`
- `write_manifest(manifest, output_path) -> None`
- Exception classes: `FletcherError`, `GitBranchError`, `ManifestNotFoundError`, `ManifestInvalidError`

---

## Error Handling

fletcher raises specific exceptions on failure:

| Exception | Cause | User sees |
|-----------|-------|-----------|
| `ManifestNotFoundError` | `.doc-gen/manifest.yml` missing or doc-gen can't be run | Error message + exit 1 |
| `ManifestInvalidError` | Manifest is malformed YAML or missing 'documents' key | Error message + exit 1 |
| `GitBranchError` | Not a git repo, empty HEAD, or git not installed | Error message + exit 1 |
| `FletcherError` | Catch-all for other fletcher errors | Error message + exit 1 |

All errors are logged before exiting.

---

## Workflow

Typical usage in a project:

```bash
# 1. Generate project documentation manifest
cd ~/projects/myproject
doc-gen

# 2. Generate GitHub URL manifest from it
fletcher --branch main --web

# 3. Upload manifest to AI assistant
# (one file, always current, under your control)

# In AI assistant:
# "I've attached myproject.fletch. Fetch all files and review the architecture."
```

---

## Dependencies

- Python 3.11+
- PyYAML >= 6.0

---

## Development

### Clone and install in dev mode

```bash
cd ~/projects/dev-utils/python/fletcher
pip install -e .
```

### Run tests (when available)

```bash
pytest tests/
```

### Code style

Follows Project Crew design rules:
- One thing per module
- No hard-coded values (config is external)
- Explicit exception handling (no bare `except`)
- 120-character line limit
- `encoding='utf-8'` on all file I/O

---

## License

MIT License. See `LICENSE` file in this directory.

---

## Part of Project Crew

fletcher is one tool in the Project Crew ecosystem:

- **doc-gen** — generates project structure documentation
- **fletcher** — generates GitHub URL manifests from doc-gen output
- **projs** — project launcher and management CLI
- **mcpkit** — config-driven MCP (Model Context Protocol) server framework
- **menukit** — YAML-driven menu library (extracted from projs)
- **dbkit** — PostgreSQL/SQLite abstraction layer
- **todo** — task manager with multiple storage backends

All tools follow the same design principles and can work together or standalone.

---

## Contributing

Contributions welcome. Please read `PROJECT_RULES.md` in the dev-utils repo before submitting.

---

## Author

Carolyn Boyle

---

## Changelog

### 0.1.0 (2025-04-18)

- Initial release
- Interactive repo selection with config persistence
- Automatic branch detection from git
- Support for raw and web URLs
- JSON and plain-text logging
- Exception hierarchy for programmatic use
