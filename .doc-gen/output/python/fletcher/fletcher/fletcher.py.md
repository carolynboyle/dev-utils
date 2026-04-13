# fletcher.py

**Path:** python/fletcher/fletcher/fletcher.py
**Syntax:** python
**Generated:** 2026-04-13 14:09:28

```python
"""
fletcher.py - GitHub URL manifest generator

Part of the dev-utils toolkit / Project Crew.
Reads a Dr. Filewalker manifest YAML and generates a .fletch manifest
with GitHub URLs for all project files.

Suitable for use by agents (raw URLs) or humans (web URLs).

Usage:
    fletcher                          (interactive — detects manifest in .doc-gen/)
    fletcher --repo https://...       (explicit repo, still warns on mismatch)
    fletcher --branch main
    fletcher --web
    fletcher --output urls.fletch

Config (~/.config/dev-utils/config.yaml):
    fletcher:
      repos:
        - https://github.com/carolynboyle/projs
        - https://github.com/carolynboyle/doc-gen
      branch: master
      url_type: raw
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


CONFIG_PATH = Path.home() / ".config" / "dev-utils" / "config.yaml"
DOC_GEN_MANIFEST = Path(".doc-gen") / "manifest.yml"

RAW_BASE = "https://raw.githubusercontent.com"
WEB_BASE = "https://github.com"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load full dev-utils config. Returns empty dict if missing."""
    if CONFIG_PATH.exists():
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text())
            return data or {}
        except (yaml.YAMLError, OSError) as e:
            print(f"Warning: could not load config {CONFIG_PATH}: {e}", file=sys.stderr)
    return {}


def save_repo_to_config(repo: str) -> None:
    """Add repo URL to saved list in config if not already present."""
    config = load_config()
    fletcher_cfg = config.setdefault("fletcher", {})
    repos = fletcher_cfg.setdefault("repos", [])

    if repo not in repos:
        repos.append(repo)
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False))
        except OSError as e:
            print(f"Warning: could not save config: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Git detection
# ---------------------------------------------------------------------------

def detect_git_repo() -> str | None:
    """
    Attempt to detect the GitHub repo URL from git remote origin.
    Returns the URL string, or None if detection fails for any reason.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # Normalise SSH to HTTPS
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):].removesuffix(".git")
        elif url.endswith(".git"):
            url = url.removesuffix(".git")
        return url if url else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# doc-gen check
# ---------------------------------------------------------------------------

def ensure_doc_gen_manifest() -> Path:
    """
    Check that .doc-gen/manifest.yml exists in the current directory.

    If missing, offer to run doc-gen interactively. Exits if the manifest
    still can't be found after doc-gen returns.
    """
    if DOC_GEN_MANIFEST.exists():
        return DOC_GEN_MANIFEST

    print(f"No {DOC_GEN_MANIFEST} found in current directory.")
    answer = input("Run doc-gen now to create it? [Y/n]: ").strip().lower()

    if answer in ("", "y", "yes"):
        try:
            subprocess.run(["doc-gen"], check=False)
        except FileNotFoundError:
            print("Error: doc-gen is not installed or not in PATH.", file=sys.stderr)
            sys.exit(1)

        if DOC_GEN_MANIFEST.exists():
            return DOC_GEN_MANIFEST

    print(
        f"Cannot continue without {DOC_GEN_MANIFEST}. "
        "Run doc-gen in this directory first, then re-run fletcher.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Repo selection
# ---------------------------------------------------------------------------

def select_repo(config: dict, cli_repo: str | None) -> str:
    """
    Determine the repo URL to use.

    Priority:
      1. --repo flag (bypass menu, but still warn on git mismatch)
      2. Git detection of current directory (offered immediately)
      3. Saved repos menu (fallback if detection fails or is declined)
      4. Manual entry
    """
    detected = detect_git_repo()

    if cli_repo:
        if detected and detected != cli_repo:
            print(
                f"Warning: --repo {cli_repo!r} does not match "
                f"detected origin {detected!r}. Continuing with --repo value."
            )
        return cli_repo

    # Priority 2: offer detected repo before anything else
    if detected:
        answer = input(
            f"Detected repo: {detected!r}\nUse this? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            save_repo_to_config(detected)
            return detected

    # Priority 3: saved repos menu
    repos = config.get("fletcher", {}).get("repos", [])
    if repos:
        print("\nSaved repos:")
        for i, r in enumerate(repos, 1):
            print(f"  {i}. {r}")
        print("  A. Enter a different repo")
        print()

        while True:
            raw = input("Selection: ").strip()
            if raw.lower() == "a":
                break
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(repos):
                    return repos[idx]
                print(f"Please enter 1-{len(repos)} or A.")
            except ValueError:
                print("Please enter a number or A.")

    # Priority 4: manual entry
    while True:
        url = input("Enter GitHub repo URL: ").strip()
        if url:
            save_repo_to_config(url)
            return url
        print("Repo URL cannot be empty.")


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

def build_raw_url(repo: str, branch: str, path: str) -> str:
    """Build a raw.githubusercontent.com URL for direct file content access."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{RAW_BASE}/{repo_path}/{branch}/{path}"


def build_web_url(repo: str, branch: str, path: str) -> str:
    """Build a github.com/blob URL for human-readable file viewing."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{WEB_BASE}/{repo_path}/blob/{branch}/{path}"


# ---------------------------------------------------------------------------
# Manifest building and writing
# ---------------------------------------------------------------------------

def build_url_manifest(paths: list, repo: str, branch: str, url_type: str) -> dict:
    """
    Build the .fletch manifest structure.

    Returns a dict ready for YAML serialization.
    Suitable for direct use by consuming scripts via import.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    build_url = build_raw_url if url_type == "raw" else build_web_url

    return {
        "repo": repo,
        "branch": branch,
        "url_type": url_type,
        "generated": now,
        "files": [
            {"path": p, "url": build_url(repo, branch, p)}
            for p in paths
        ],
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point: resolve manifest, repo, and options, then generate the .fletch URL manifest."""
    parser = argparse.ArgumentParser(
        description="Generate a GitHub URL manifest (.fletch) from a Dr. Filewalker manifest.",
        epilog="Config: ~/.config/dev-utils/config.yaml",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo URL — bypasses saved repo menu, warns if it mismatches git origin",
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
        help="Output file path (default: .doc-gen/<manifest>.fletch)",
    )

    args = parser.parse_args()

    # Step 1 — ensure doc-gen manifest exists
    manifest_path = ensure_doc_gen_manifest()

    # Step 2 — load config
    config = load_config()
    fletcher_cfg = config.get("fletcher", {})

    # Step 3 — resolve repo
    repo = select_repo(config, args.repo)

    # Step 4 — resolve branch and url_type
    branch = args.branch or fletcher_cfg.get("branch", "master")
    url_type = "web" if args.web else fletcher_cfg.get("url_type", "raw")

    # Step 5 — resolve output path
    output_path = args.output or default_output_path(manifest_path)

    # Step 6 — build and write
    paths = load_manifest(manifest_path)
    manifest = build_url_manifest(paths, repo, branch, url_type)
    write_manifest(manifest, output_path)


if __name__ == "__main__":
    main()

```
