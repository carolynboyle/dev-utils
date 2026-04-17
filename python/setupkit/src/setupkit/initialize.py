"""
setupkit.initialize - Interactive plugin config generator for setupkit.

Guides the user through creating a plugin config yaml in
~/.config/dev-utils/setupkit/<n>.yaml by fetching the upstream
manifest.fletch and presenting its file list for path selection.

Workflow:
    1. Prompt for manifest_url (or detect from git remote)
    2. Fetch manifest.fletch
    3. Read name and version from manifest
    4. Present file list and prompt for path_prefix selection
    5. Infer pyproject path from path_prefix
    6. Prompt for install url
    7. If config already exists, show diff and confirm overwrite
    8. Write ~/.config/dev-utils/setupkit/<n>.yaml

Public API:
    init_plugin — run the interactive init flow for a named plugin
"""

import subprocess
import sys
from pathlib import Path

import yaml

from setupkit.exceptions import ManifestError, PluginConfigError
from setupkit.manifest import fetch_manifest
from setupkit.config import ConfigManager
from setupkit.installer import config_path

_config    = ConfigManager()
CONFIG_DIR = _config.config_dir


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_plugin(name: str) -> None:
    """
    Run the interactive init flow for a named plugin.

    Guides the user through creating a plugin config yaml by fetching
    the upstream manifest.fletch and presenting its file list for
    path prefix selection. Writes the result to
    ~/.config/dev-utils/setupkit/<n>.yaml.

    Args:
        name: Plugin name (e.g. 'dbkit').

    Raises:
        PluginConfigError: If the config cannot be written.
        ManifestError:     If manifest.fletch cannot be fetched or parsed.
    """
    print(f"\nsetupkit init — configuring plugin: {name}")
    print("=" * 50)

    # Step 1 — manifest URL
    manifest_url = _prompt_manifest_url(name)

    # Step 2 — fetch manifest
    print(f"\nFetching manifest from {manifest_url} ...")
    try:
        manifest = fetch_manifest(manifest_url)
    except ManifestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(manifest.files)} files")
    if manifest.version:
        print(f"Upstream version: {manifest.version}")
    else:
        print("Warning: manifest has no version field")

    # Step 3 — path prefix selection
    path_prefix = _select_path_prefix(manifest.files, name)

    # Step 4 — infer pyproject path
    pyproject = _infer_pyproject(path_prefix, manifest.files)

    # Step 5 — install URL
    install_url = _prompt_install_url(name, manifest.repo)

    # Step 6 — build config dict
    config = {
        "name": name,
        "version": manifest.version or "0.1.0",
        "manifest_url": manifest_url,
        "pyproject": pyproject,
        "path_prefix": path_prefix,
        "install": {
            "method": "pip",
            "url": install_url,
        },
    }

    # Step 7 — check for existing config and confirm overwrite
    dest = config_path(name)
    if dest.exists():
        _confirm_overwrite(dest, config)

    # Step 8 — write config
    _write_config(dest, config)


# ---------------------------------------------------------------------------
# Interactive helpers
# ---------------------------------------------------------------------------

def _prompt_manifest_url(name: str) -> str:
    """
    Prompt for the manifest.fletch URL, offering a git-detected default.

    Args:
        name: Plugin name, used in the prompt.

    Returns:
        The manifest URL string entered or confirmed by the user.
    """
    detected = _detect_git_repo()

    if detected:
        default_url = f"{detected}/raw/master/.doc-gen/manifest.fletch"
        print(f"\nDetected repo: {detected}")
        answer = input(
            f"Use manifest URL {default_url!r}? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            return default_url

    while True:
        url = input("\nEnter manifest.fletch raw URL: ").strip()
        if url:
            return url
        print("URL cannot be empty.")


def _select_path_prefix(files: list, name: str) -> str:
    """
    Present the manifest file list and prompt the user to select a path prefix.

    Groups files by their top-level path components to make selection easier.
    Allows the user to select from common prefixes or enter one manually.

    Args:
        files: List of ManifestFile entries from the fetched manifest.
        name:  Plugin name, used to suggest a likely prefix.

    Returns:
        The selected path prefix string.
    """
    # Extract unique top-level prefixes (up to 3 path components)
    prefixes: dict[str, int] = {}
    for f in files:
        parts = Path(f.path).parts
        if len(parts) >= 3:
            prefix = str(Path(*parts[:3])) + "/"
            prefixes[prefix] = prefixes.get(prefix, 0) + 1

    # Sort by file count descending
    sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)

    # Suggest the prefix most likely to match the plugin name
    suggested = next(
        (p for p, _ in sorted_prefixes if name in p.lower()),
        None,
    )

    print(f"\nCommon path prefixes in manifest ({len(files)} files total):")
    for i, (prefix, count) in enumerate(sorted_prefixes, 1):
        marker = " ◀ suggested" if prefix == suggested else ""
        print(f"  {i}. {prefix} ({count} files){marker}")
    print(f"  M. Enter manually")
    print()

    while True:
        raw = input("Select path prefix: ").strip()

        if raw.lower() == "m":
            break
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(sorted_prefixes):
                selected = sorted_prefixes[idx][0]
                confirm = input(f"Use {selected!r}? [Y/n]: ").strip().lower()
                if confirm in ("", "y", "yes"):
                    return selected
            else:
                print(f"Please enter 1-{len(sorted_prefixes)} or M.")
        except ValueError:
            print(f"Please enter a number or M.")

    while True:
        prefix = input("Enter path prefix (e.g. python/dbkit/dbkit/): ").strip()
        if prefix:
            if not prefix.endswith("/"):
                prefix += "/"
            return prefix
        print("Path prefix cannot be empty.")


def _infer_pyproject(path_prefix: str, files: list) -> str:
    """
    Infer the pyproject.toml path from the selected path prefix.

    Walks up the prefix path looking for a pyproject.toml in the manifest.
    Prompts the user to confirm or correct the inferred path.

    Args:
        path_prefix: The selected source file path prefix.
        files:       List of ManifestFile entries from the manifest.

    Returns:
        The confirmed pyproject.toml path string.
    """
    file_paths = {f.path for f in files}

    # Walk up the prefix to find pyproject.toml
    parts = Path(path_prefix.rstrip("/")).parts
    inferred = None
    for i in range(len(parts), 0, -1):
        candidate = str(Path(*parts[:i]) / "pyproject.toml")
        if candidate in file_paths:
            inferred = candidate
            break

    if inferred:
        print(f"\nInferred pyproject.toml path: {inferred}")
        confirm = input("Use this? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            return inferred

    print("\nAvailable pyproject.toml files in manifest:")
    pyprojects = [f.path for f in files if f.path.endswith("pyproject.toml")]
    for i, p in enumerate(pyprojects, 1):
        print(f"  {i}. {p}")
    print("  M. Enter manually")

    while True:
        raw = input("Select pyproject.toml: ").strip()
        if raw.lower() == "m":
            break
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(pyprojects):
                return pyprojects[idx]
            print(f"Please enter 1-{len(pyprojects)} or M.")
        except ValueError:
            print("Please enter a number or M.")

    while True:
        path = input("Enter pyproject.toml path: ").strip()
        if path:
            return path
        print("Path cannot be empty.")


def _prompt_install_url(name: str, repo: str) -> str:
    """
    Prompt for the pip install URL, offering a git+ default derived from
    the manifest repo and plugin name.

    Args:
        name: Plugin name (e.g. 'dbkit').
        repo: Repo URL from the manifest (e.g. 'https://github.com/carolynboyle/dev-utils').

    Returns:
        The install URL string entered or confirmed by the user.
    """
    default = f"git+{repo}.git#subdirectory=python/{name}"
    print(f"\nSuggested install URL: {default}")
    answer = input("Use this? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        return default

    while True:
        url = input("Enter pip install URL: ").strip()
        if url:
            return url
        print("URL cannot be empty.")


def _confirm_overwrite(dest: Path, new_config: dict) -> None:
    """
    Show a diff between the existing config and the new config,
    then prompt the user to confirm overwrite.

    Exits without writing if the user declines.

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


# ---------------------------------------------------------------------------
# Git detection
# ---------------------------------------------------------------------------

def _detect_git_repo() -> str | None:
    """
    Attempt to detect the GitHub repo URL from git remote origin.

    Returns the normalised HTTPS URL, or None if detection fails.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):].removesuffix(".git")
        elif url.endswith(".git"):
            url = url.removesuffix(".git")
        return url if url else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _write_config(dest: Path, config: dict) -> None:
    """
    Write a plugin config dict to disk as YAML.

    Creates the config directory if it does not exist.

    Args:
        dest:   Destination path for the config file.
        config: Config dict to serialise.

    Raises:
        PluginConfigError: If the file cannot be written.
    """
    header = (
        f"# setupkit plugin config — generated by setupkit init\n"
        f"# Edit manually or regenerate with: setupkit init {config['name']}\n\n"
    )
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            header + yaml.dump(config, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        print(f"\nWritten: {dest}")
        print(f"Install with: setupkit install {config['name']}")
    except OSError as exc:
        raise PluginConfigError(f"Could not write config {dest}: {exc}") from exc
