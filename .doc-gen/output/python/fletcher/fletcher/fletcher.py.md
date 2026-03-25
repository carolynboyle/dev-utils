# fletcher.py

**Path:** python/fletcher/fletcher/fletcher.py
**Syntax:** python
**Generated:** 2026-03-23 18:05:03

```python
"""
fletcher.py - GitHub URL manifest generator

Part of the dev-utils toolkit / Project Crew.
Reads a Dr. Filewalker manifest YAML and generates a .fletch manifest
with GitHub URLs for all project files.

Suitable for use by agents (raw URLs) or humans (web URLs).

Usage:
    fletcher manifest.yml
    fletcher manifest.yml --web
    fletcher manifest.yml --branch main
    fletcher manifest.yml --repo https://github.com/user/repo
    fletcher manifest.yml --output urls.fletch

Config (~/.config/dev-utils/config.yaml):
    fletcher:
      repo: https://github.com/carolynboyle/projs
      branch: master
      url_type: raw
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml


CONFIG_PATH = Path.home() / ".config" / "dev-utils" / "config.yaml"

RAW_BASE = "https://raw.githubusercontent.com"
WEB_BASE = "https://github.com"


def load_config() -> dict:
    """
    Load dev-utils config from ~/.config/dev-utils/config.yaml.
    Returns empty fletcher section if file doesn't exist.
    """
    if CONFIG_PATH.exists():
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text())
            if data:
                return data.get("fletcher", {})
        except (yaml.YAMLError, OSError) as e:
            print(f"Warning: could not load config {CONFIG_PATH}: {e}", file=sys.stderr)
    return {}


def load_manifest(manifest_path: Path) -> list:
    """
    Load a Dr. Filewalker manifest YAML.
    Returns list of path strings.
    """
    try:
        data = yaml.safe_load(manifest_path.read_text())
        if not data or "documents" not in data:
            print(f"Error: no 'documents' key found in {manifest_path}", file=sys.stderr)
            sys.exit(1)
        return [doc["path"] for doc in data["documents"] if "path" in doc]
    except (yaml.YAMLError, OSError) as e:
        print(f"Error: could not load manifest {manifest_path}: {e}", file=sys.stderr)
        sys.exit(1)


def build_raw_url(repo: str, branch: str, path: str) -> str:
    """Build a raw.githubusercontent.com URL for direct file content access."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{RAW_BASE}/{repo_path}/{branch}/{path}"


def build_web_url(repo: str, branch: str, path: str) -> str:
    """Build a github.com/blob URL for human-readable file viewing."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{WEB_BASE}/{repo_path}/blob/{branch}/{path}"


def build_url_manifest(
    paths: list,
    repo: str,
    branch: str,
    url_type: str,
) -> dict:
    """
    Build the .fletch manifest structure.

    Returns a dict ready for YAML serialization.
    Suitable for direct use by consuming scripts via import.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    build_url = build_raw_url if url_type == "raw" else build_web_url

    files = [
        {"path": path, "url": build_url(repo, branch, path)}
        for path in paths
    ]

    return {
        "repo": repo,
        "branch": branch,
        "url_type": url_type,
        "generated": now,
        "files": files,
    }


def write_manifest(manifest: dict, output_path: Path) -> None:
    """
    Write the .fletch manifest to disk.

    Output is valid YAML with a human-readable comment header.
    Any YAML parser can read it — the .fletch extension is identity, not format.
    """
    header = (
        f"# Generated: {manifest['generated']}\n"
        f"# Repo: {manifest['repo']}\n"
        f"# Branch: {manifest['branch']}\n"
        f"# URL type: {manifest['url_type']}\n"
        f"# Files: {len(manifest['files'])}\n\n"
    )

    try:
        output_path.write_text(
            header + yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )
        print(f"Written: {output_path} ({len(manifest['files'])} files)")
    except OSError as e:
        print(f"Error: could not write {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


def default_output_path(manifest_path: Path) -> Path:
    """Generate default output path alongside the input manifest."""
    return manifest_path.parent / f"{manifest_path.stem}.fletch"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a GitHub URL manifest (.fletch) from a Dr. Filewalker manifest.",
        epilog="Config: ~/.config/dev-utils/config.yaml",
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to Dr. Filewalker manifest YAML",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo URL (e.g. https://github.com/user/repo)",
    )
    parser.add_argument(
        "--branch",
        help="Branch name (default: from config or 'master')",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Generate web URLs for humans instead of raw URLs for agents",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: <manifest>.fletch)",
    )

    args = parser.parse_args()

    config = load_config()

    repo = args.repo or config.get("repo")
    if not repo:
        print("Error: repo URL required. Set in config or pass --repo.", file=sys.stderr)
        sys.exit(1)

    branch = args.branch or config.get("branch", "master")
    url_type = "web" if args.web else config.get("url_type", "raw")

    manifest_path = args.manifest
    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or default_output_path(manifest_path)

    paths = load_manifest(manifest_path)
    manifest = build_url_manifest(paths, repo, branch, url_type)
    write_manifest(manifest, output_path)


if __name__ == "__main__":
    main()

```
