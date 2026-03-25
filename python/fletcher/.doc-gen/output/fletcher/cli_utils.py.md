# cli_utils.py

**Path:** fletcher/cli_utils.py
**Syntax:** python
**Generated:** 2026-03-20 12:22:02

```python
"""
fetcher.py - GitHub URL manifest generator

Part of the dev-utils toolkit / Project Crew.
Reads a Dr. Filewalker manifest YAML and generates a URL manifest
for all project files, suitable for use by agents or humans.

Usage:
    fetcher.py manifest.yml
    fetcher.py manifest.yml --web
    fetcher.py manifest.yml --branch main
    fetcher.py manifest.yml --repo https://github.com/user/repo
    fetcher.py manifest.yml --output urls.yaml

Config (~/.config/dev-utils/config.yaml):
    fetcher:
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
    Returns empty fetcher section if file doesn't exist.
    """
    if CONFIG_PATH.exists():
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text())
            if data:
                return data.get("fetcher", {})
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
    """Build the output manifest structure."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    build_url = build_raw_url if url_type == "raw" else build_web_url

    files = [
        {"path": path, "url": build_url(repo, branch, path)}
        for path in paths
    ]

    return {
        "_generated": now,
        "repo": repo,
        "branch": branch,
        "url_type": url_type,
        "generated": now,
        "files": files,
    }


def write_manifest(manifest: dict, output_path: Path) -> None:
    """Write the URL manifest to a YAML file with header comments."""
    header = (
        f"# Generated: {manifest['generated']}\n"
        f"# Repo: {manifest['repo']}\n"
        f"# Branch: {manifest['branch']}\n"
        f"# URL type: {manifest['url_type']}\n"
        f"# Files: {len(manifest['files'])}\n\n"
    )

    data = {k: v for k, v in manifest.items() if not k.startswith("_")}

    try:
        output_path.write_text(header + yaml.dump(data, default_flow_style=False, sort_keys=False))
        print(f"Written: {output_path} ({len(manifest['files'])} files)")
    except OSError as e:
        print(f"Error: could not write {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


def default_output_path(manifest_path: Path, url_type: str) -> Path:
    """Generate a default output filename alongside the input manifest."""
    stem = manifest_path.stem
    return manifest_path.parent / f"{stem}-{url_type}-urls.yaml"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a GitHub URL manifest from a Dr. Filewalker manifest.",
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
        help="Output file path (default: <manifest>-<type>-urls.yaml)",
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

    output_path = args.output or default_output_path(manifest_path, url_type)

    paths = load_manifest(manifest_path)
    manifest = build_url_manifest(paths, repo, branch, url_type)
    write_manifest(manifest, output_path)


if __name__ == "__main__":
    main()

```
