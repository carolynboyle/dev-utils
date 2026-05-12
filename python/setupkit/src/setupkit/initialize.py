"""
setupkit.initialize - Plugin config generator for setupkit.

Generates a plugin config yaml in ~/.config/dev-utils/setupkit/<name>.yaml
by reading the setupkit-registry.yaml from the upstream repo. All values
are derived automatically from the registry — no interactive prompts are
needed for packages listed there.

For packages not in the registry, falls back to interactive prompts.

Workflow (registry path):
    1. Fetch setupkit-registry.yaml from upstream repo
    2. Look up package entry by name
    3. Derive all config values from registry entry
    4. Fetch manifest.fletch to confirm upstream version
    5. If config already exists, show diff and confirm overwrite
    6. Write ~/.config/dev-utils/setupkit/<name>.yaml

Workflow (fallback path):
    1. Detect git remote or prompt for manifest URL
    2. Fetch manifest.fletch
    3. Present file list and prompt for path_prefix selection
    4. Infer pyproject path from path_prefix
    5. Prompt for install URL
    6. If config already exists, show diff and confirm overwrite
    7. Write ~/.config/dev-utils/setupkit/<name>.yaml

Public API:
    init_plugin — generate a plugin config for a named plugin
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests
import yaml

from setupkit.exceptions import ManifestError, PluginConfigError
from setupkit.manifest import fetch_manifest
from setupkit.config import ConfigManager
from setupkit.installer import config_path

_config    = ConfigManager()
CONFIG_DIR = _config.config_dir

# Raw URL to the registry file in the upstream repo.
# Derived from the repo URL if detection succeeds; this constant is
# the fallback for machines not running from within a git clone.
_REGISTRY_FILENAME = "setupkit-registry.yaml"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_plugin(name: str) -> None:
    """
    Generate a plugin config for a named plugin.

    Attempts to read the setupkit-registry.yaml from the upstream repo
    and derive all config values automatically. Falls back to interactive
    prompts if the registry is unavailable or the package is not listed.

    Args:
        name: Plugin name (e.g. 'treekit').

    Raises:
        PluginConfigError: If the config cannot be written.
        ManifestError:     If manifest.fletch cannot be fetched or parsed.
    """
    print(f"\nsetupkit init — configuring plugin: {name}")
    print("=" * 50)

    # --- Try registry path first --------------------------------------------
    registry = _load_registry()

    if registry and name in registry.get("packages", {}):
        _init_from_registry(name, registry)
    else:
        if registry and name not in registry.get("packages", {}):
            print(f"\nWarning: {name!r} not found in registry — falling back to interactive mode.")
        _init_interactive(name)


# ---------------------------------------------------------------------------
# Registry-driven init
# ---------------------------------------------------------------------------

def _init_from_registry(name: str, registry: dict) -> None:
    """
    Generate a plugin config from a registry entry.

    Derives all config values from the registry without prompting.
    Fetches manifest.fletch to confirm the upstream version.

    Args:
        name:     Plugin name.
        registry: Parsed registry dict from setupkit-registry.yaml.
    """
    repo   = registry["repo"]
    branch = registry["branch"]
    manifest_path = registry["manifest"]
    entry  = registry["packages"][name]
    path   = entry["path"]

    manifest_url = f"{repo}/raw/{branch}/{manifest_path}"
    pyproject    = f"{path}/pyproject.toml"
    path_prefix  = f"{path}/src/{name}/"
    install_url  = f"git+{repo}.git#subdirectory={path}"

    print(f"\nFound {name!r} in registry.")
    print(f"  path_prefix:  {path_prefix}")
    print(f"  pyproject:    {pyproject}")
    print(f"  install URL:  {install_url}")
    print(f"  manifest URL: {manifest_url}")

    # Fetch manifest to get upstream version.
    print(f"\nFetching manifest...")
    try:
        manifest = fetch_manifest(manifest_url)
    except ManifestError as exc:
        print(f"Error fetching manifest: {exc}", file=sys.stderr)
        sys.exit(1)

    version = manifest.version or "0.1.0"
    print(f"Upstream version: {version}")

    config = {
        "name": name,
        "version": version,
        "manifest_url": manifest_url,
        "pyproject": pyproject,
        "path_prefix": path_prefix,
        "install": {
            "method": "pip",
            "url": install_url,
        },
    }

    dest = config_path(name)
    if dest.exists():
        _confirm_overwrite(dest, config)

    _write_config(dest, config)


def _load_registry() -> Optional[dict]:
    """
    Attempt to fetch and parse setupkit-registry.yaml from the upstream repo.

    Tries to detect the repo URL from git remote first. If that fails,
    checks whether a local copy exists alongside setup.sh in the repo root.

    Returns:
        Parsed registry dict, or None if the registry cannot be loaded.
    """
    # Try git remote detection first.
    repo_url = _detect_git_repo()

    if repo_url:
        registry_url = f"{repo_url}/raw/main/{_REGISTRY_FILENAME}"
        try:
            response = requests.get(registry_url, timeout=10)
            response.raise_for_status()
            data = yaml.safe_load(response.text)
            if isinstance(data, dict) and "packages" in data:
                return data
        except (requests.RequestException, yaml.YAMLError):
            pass

    # Try local file alongside the script (useful during bootstrap).
    local_candidates = [
        Path(__file__).parent.parent.parent.parent / _REGISTRY_FILENAME,
        Path.cwd() / _REGISTRY_FILENAME,
    ]
    for candidate in local_candidates:
        if candidate.exists():
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "packages" in data:
                    return data
            except (yaml.YAMLError, OSError):
                pass

    return None


# ---------------------------------------------------------------------------
# Interactive fallback init
# ---------------------------------------------------------------------------

def _init_interactive(name: str) -> None:
    """
    Generate a plugin config interactively when registry is unavailable.

    Guides the user through each config value with prompts.

    Args:
        name: Plugin name.
    """
    manifest_url = _prompt_manifest_url(name)

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

    path_prefix = _select_path_prefix(manifest.files, name)
    pyproject   = _infer_pyproject(path_prefix, manifest.files)
    install_url = _prompt_install_url(name, manifest.repo)

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

    dest = config_path(name)
    if dest.exists():
        _confirm_overwrite(dest, config)

    _write_config(dest, config)


# ---------------------------------------------------------------------------
# Interactive helpers (fallback path only)
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
        default_url = f"{detected}/raw/main/.doc-gen/manifest.fletch"
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

    Args:
        files: List of ManifestFile entries from the fetched manifest.
        name:  Plugin name, used to suggest a likely prefix.

    Returns:
        The selected path prefix string.
    """
    prefixes: dict[str, int] = {}
    for f in files:
        parts = Path(f.path).parts
        if len(parts) >= 3:
            prefix = str(Path(*parts[:3])) + "/"
            prefixes[prefix] = prefixes.get(prefix, 0) + 1

    sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)

    suggested = next(
        (p for p, _ in sorted_prefixes if name in p.lower()),
        None,
    )

    print(f"\nCommon path prefixes in manifest ({len(files)} files total):")
    for i, (prefix, count) in enumerate(sorted_prefixes, 1):
        marker = " ◀ suggested" if prefix == suggested else ""
        print(f"  {i}. {prefix} ({count} files){marker}")
    print("  M. Enter manually")
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
            print("Please enter a number or M.")

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

    Args:
        path_prefix: The selected source file path prefix.
        files:       List of ManifestFile entries from the manifest.

    Returns:
        The confirmed pyproject.toml path string.
    """
    file_paths = {f.path for f in files}

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
    Prompt for the pip install URL, offering a git+ default.

    Args:
        name: Plugin name (e.g. 'dbkit').
        repo: Repo URL from the manifest.

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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _confirm_overwrite(dest: Path, new_config: dict) -> None:
    """
    Show existing and new config, prompt to confirm overwrite.

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


def _detect_git_repo() -> Optional[str]:
    """
    Attempt to detect the GitHub repo URL from git remote origin.

    Returns:
        Normalised HTTPS URL, or None if detection fails.
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


def _write_config(dest: Path, config: dict) -> None:
    """
    Write a plugin config dict to disk as YAML.

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
