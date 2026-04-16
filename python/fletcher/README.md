# fletcher

GitHub URL manifest generator for the dev-utils toolkit / Project Crew.

Reads a [Dr. Filewalker](https://github.com/carolynboyle/doc-gen) manifest and generates a
`.fletch` manifest mapping every project file to its GitHub raw or web URL. The `.fletch`
file is valid YAML and can be consumed by agents, scripts, or the Project Crew plugin
installer.

---

## Requirements

- Python 3.11 or later (uses `tomllib` from the standard library)
- `pyyaml >= 6.0`
- A [Dr. Filewalker](https://github.com/carolynboyle/doc-gen) `.doc-gen/manifest.yml` in
  the directory where fletcher is run

---

## Installation

From the dev-utils repo:

```bash
pip install -e ~/projects/dev-utils/python/fletcher
```

Or from anywhere:

```bash
pip install -e git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/fletcher
```

---

## Usage

```
fletcher [--repo URL] [--branch NAME] [--web] [--output PATH]
```

Run from the root of a project that has a `.doc-gen/manifest.yml`. If no manifest is found,
fletcher will offer to run `doc-gen` to create one.

### Options

| Flag | Description |
|---|---|
| `--repo URL` | GitHub repo URL. Bypasses the saved repo menu. Warns if it does not match the detected `git remote origin`. |
| `--branch NAME` | Branch name. Defaults to the value in config, or `master`. |
| `--web` | Generate `github.com/blob/` URLs for human browsing instead of `raw.githubusercontent.com` URLs for agents. |
| `--output PATH` | Output file path. Defaults to `.doc-gen/manifest.fletch`. |

### Example

```bash
cd ~/projects/dev-utils/python/fletcher
fletcher
# Written: .doc-gen/manifest.fletch (12 files, v0.1.0)
```

---

## Output format

The `.fletch` file is valid YAML with a comment header for quick human inspection:

```yaml
# Generated: 2026-04-16 14:32:01
# Repo: https://github.com/carolynboyle/dev-utils
# Branch: master
# URL type: raw
# Version: v0.1.0
# Files: 12

repo: https://github.com/carolynboyle/dev-utils
branch: master
url_type: raw
generated: '2026-04-16 14:32:01'
version: 0.1.0
files:
  - path: python/fletcher/fletcher/__init__.py
    url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/fletcher/fletcher/__init__.py
  - path: python/fletcher/fletcher/fletcher.py
    url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/fletcher/fletcher/fletcher.py
```

The `version` field is read from `pyproject.toml` in the current directory at generation
time. If no `pyproject.toml` is found, or it contains no `[project].version` field, the
field is omitted and a warning is logged.

---

## Configuration

Fletcher reads from `~/.config/dev-utils/config.yaml` and saves repo URLs between runs:

```yaml
fletcher:
  repos:
    - https://github.com/carolynboyle/dev-utils
    - https://github.com/carolynboyle/projs
  branch: master
  url_type: raw
```

All fields are optional. Fletcher will prompt interactively for anything not configured.

---

## Logging

Fletcher writes two log files to `~/.local/share/dev-utils/`:

| File | Format | Use |
|---|---|---|
| `fletcher.log` | Plain text, one line per event | Day-to-day reading |
| `fletcher.json.log` | One JSON object per line | Machine consumption, future Ansible integration |

Both logs are at `INFO` level. Warnings and errors also print to stderr.

Plain text format:
```
2026-04-16 14:32:01 [INFO] fletcher started
2026-04-16 14:32:01 [INFO] Read version 0.1.0 from pyproject.toml
2026-04-16 14:32:01 [INFO] Written: .doc-gen/manifest.fletch (12 files, v0.1.0)
2026-04-16 14:32:01 [INFO] fletcher finished
```

JSON format:
```json
{"timestamp": "2026-04-16T14:32:01", "level": "INFO", "tool": "fletcher", "message": "fletcher started"}
{"timestamp": "2026-04-16T14:32:01", "level": "INFO", "tool": "fletcher", "message": "Read version 0.1.0 from pyproject.toml"}
```

---

## Recommended workflow

Fletcher is intended to be run before every GitHub sync so that `manifest.fletch` is always
current in the repo:

```bash
cd ~/projects/dev-utils/python/fletcher
fletcher
git add .doc-gen/manifest.fletch
git commit -m "chore: update manifest.fletch"
git push
```

A pre-push git hook can automate this. See `docs/` for an example hook (forthcoming).

---

## Public API

Fletcher can also be used as a library:

```python
from fletcher import build_url_manifest, write_manifest
from pathlib import Path

paths = ["fletcher/__init__.py", "fletcher/fletcher.py"]
manifest = build_url_manifest(
    paths=paths,
    repo="https://github.com/carolynboyle/dev-utils",
    branch="master",
    url_type="raw",
)
write_manifest(manifest, Path("manifest.fletch"))
```

### `build_url_manifest(paths, repo, branch, url_type) -> dict`

Builds the manifest structure. Reads `version` from `pyproject.toml` in the current
directory if available. Returns a dict ready for YAML serialization.

### `write_manifest(manifest, output_path) -> None`

Writes the manifest dict to disk as YAML with a comment header.

---

## Part of dev-utils

fletcher is one of several tools in the
[dev-utils](https://github.com/carolynboyle/dev-utils) toolkit:

| Tool | Description |
|---|---|
| **fletcher** | GitHub URL manifest generator |
| **dbkit** | PostgreSQL connection and query utilities |
| **viewkit** | YAML-driven view definition library |
| **menukit** | Interactive CLI menu builder |
| **mcpkit** | MCP server toolkit |
