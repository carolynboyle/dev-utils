# setupkit URL Construction Bug Fixes

## Summary

Three bugs all stem from the same root cause: `setupkit-registry.yaml` now stores
the repo URL with a `.git` suffix (`https://github.com/carolynboyle/dev-utils.git`),
but `_init_from_registry()` in `initialize.py` was written when the registry used
a bare SSH URL without `.git`. The URL-building code didn't account for `.git`
already being present, producing broken manifest and install URLs.

A fourth fix removes the SSH transform from `installer.py` that was missed in the
previous commit.

---

## File 1: `python/setupkit/src/setupkit/initialize.py`

### Change 1 — Fix manifest URL (`.git` in raw URL)

**Location:** `_init_from_registry()`, line 108

**BEFORE:**
```python
manifest_url = f"{repo}/raw/{branch}/{manifest_path}"
```

**AFTER:**
```python
repo_base    = repo.removesuffix(".git")
manifest_url = f"{repo_base}/raw/{branch}/{manifest_path}"
```

**Why:** GitHub raw URLs do not include `.git`. With the registry `repo` value set
to `https://github.com/carolynboyle/dev-utils.git`, the old code produced:

```
https://github.com/carolynboyle/dev-utils.git/raw/main/.doc-gen/manifest.fletch
```

which returns HTTP 404. Stripping `.git` first produces the correct URL:

```
https://github.com/carolynboyle/dev-utils/raw/main/.doc-gen/manifest.fletch
```

---

### Change 2 — Fix install URL (double `.git`)

**Location:** `_init_from_registry()`, line 111

**BEFORE:**
```python
install_url = f"{name} @ git+{repo}.git#subdirectory={path}"
```

**AFTER:**
```python
install_url = f"{name} @ git+{repo}#subdirectory={path}"
```

**Why:** `repo` already ends in `.git`, so the old code appended another one,
producing:

```
dbkit @ git+https://github.com/carolynboyle/dev-utils.git.git#subdirectory=python/dbkit
```

Pip rejected this as an invalid VCS URL. Removing the hardcoded `.git` suffix lets
the registry value pass through unchanged.

---

### Complete `_init_from_registry()` function — BEFORE:

```python
def _init_from_registry(name: str, registry: dict) -> None:
    repo   = registry["repo"]
    branch = registry["branch"]
    manifest_path = registry["manifest"]
    entry  = registry["packages"][name]
    path   = entry["path"]

    manifest_url = f"{repo}/raw/{branch}/{manifest_path}"
    pyproject    = f"{path}/pyproject.toml"
    path_prefix  = f"{path}/src/{name}/"
    install_url  = f"{name} @ git+{repo}.git#subdirectory={path}"
    ...
```

### Complete `_init_from_registry()` function — AFTER:

```python
def _init_from_registry(name: str, registry: dict) -> None:
    repo   = registry["repo"]
    branch = registry["branch"]
    manifest_path = registry["manifest"]
    entry  = registry["packages"][name]
    path   = entry["path"]

    repo_base    = repo.removesuffix(".git")
    manifest_url = f"{repo_base}/raw/{branch}/{manifest_path}"
    pyproject    = f"{path}/pyproject.toml"
    path_prefix  = f"{path}/src/{name}/"
    install_url  = f"{name} @ git+{repo}#subdirectory={path}"
    ...
```

---

## File 2: `python/setupkit/src/setupkit/installer.py`

### Change 3 — Remove SSH transform (missed in previous commit)

The `_transform_git_url_to_ssh()` function was meant to be removed in the previous
commit but the updated `installer.py` was not pushed.

**BEFORE — remove this entire function:**
```python
def _transform_git_url_to_ssh(url: str) -> str:
    """
    Transform a git+https:// URL to bare SSH URL for pip install.
    ...
    """
    if "git+https://github.com/" in url:
        return url.replace(
            "git+https://github.com/",
            "git+git@github.com:"
        )
    return url
```

**BEFORE — `_run_pip_install()` calls the transform:**
```python
def _run_pip_install(config: PluginConfig) -> None:
    """
    Run pip install for a plugin using the install URL from plugin config.

    Transforms HTTPS git URLs to SSH before passing to pip.
    ...
    """
    install_url = _transform_git_url_to_ssh(config.install.url)
    cmd = [sys.executable, "-m", "pip", "install", "-e", install_url]
    ...
```

**AFTER — `_run_pip_install()` uses the URL directly:**
```python
def _run_pip_install(config: PluginConfig) -> None:
    """
    Run pip install for a plugin using the install URL from plugin config.

    Uses the same Python interpreter that is running setupkit to ensure
    the package is installed into the correct environment.
    ...
    """
    install_url = config.install.url
    cmd = [sys.executable, "-m", "pip", "install", "-e", install_url]
    ...
```

**Why:** The SSH transform was producing invalid pip VCS URLs
(`git+git@github.com:` is not a valid pip scheme). Since dev-utils is a public
repo, HTTPS works without credentials and pip handles it natively. No transform
needed.

---

## After applying these changes

```bash
# Delete stale plugin configs
rm -f ~/.config/dev-utils/setupkit/*.yaml

# Reinstall setupkit to pick up the code changes
pip install -e python/setupkit --force-reinstall

# Re-init and install all plugins
setupkit init dbkit
setupkit init fletcher
setupkit init menukit
setupkit init sniffkit
setupkit init treekit
setupkit init viewkit
setupkit install
```
