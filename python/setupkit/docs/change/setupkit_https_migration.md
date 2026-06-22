# setupkit HTTPS Migration — Change Documentation

## Summary
Migrate from SSH git URLs to HTTPS for pip compatibility. This eliminates the broken `_transform_git_url_to_ssh()` function and uses HTTPS URLs that pip handles natively.

---

## File 1: setupkit-registry.yaml

### BEFORE
```yaml
# setupkit-registry.yaml — installable packages in the dev-utils repo.
#
# This file is the single source of truth for what setupkit can install.
# Add a new entry here when a new package is added to the repo.
#
# All values below are repo-wide defaults. Individual entries only need
# to specify name and path. All other fields are derived automatically:
#
#   manifest_url  → {repo}/raw/{branch}/{manifest}
#   pyproject     → {path}/pyproject.toml
#   path_prefix   → {path}/src/{name}/
#   install.url   → git+{repo}.git#subdirectory={path}


repo: git@github.com:carolynboyle/dev-utils.git
branch: main
manifest: .doc-gen/manifest.fletch

packages:
  dbkit:
    path: python/dbkit
  fletcher:
    path: python/fletcher
  menukit:
    path: python/menukit
  setupkit:
    path: python/setupkit
  sniffkit:
    path: python/sniffkit
  treekit:
    path: python/treekit
  viewkit:
    path: python/viewkit
```

### AFTER
```yaml
# setupkit-registry.yaml — installable packages in the dev-utils repo.
#
# This file is the single source of truth for what setupkit can install.
# Add a new entry here when a new package is added to the repo.
#
# All values below are repo-wide defaults. Individual entries only need
# to specify name and path. All other fields are derived automatically:
#
#   manifest_url  → {repo}/raw/{branch}/{manifest}
#   pyproject     → {path}/pyproject.toml
#   path_prefix   → {path}/src/{name}/
#   install.url   → git+{repo}.git#subdirectory={path}


repo: https://github.com/carolynboyle/dev-utils.git
branch: main
manifest: .doc-gen/manifest.fletch

packages:
  dbkit:
    path: python/dbkit
  fletcher:
    path: python/fletcher
  menukit:
    path: python/menukit
  setupkit:
    path: python/setupkit
  sniffkit:
    path: python/sniffkit
  treekit:
    path: python/treekit
  viewkit:
    path: python/viewkit
```

### Change Explanation
**Line 12:** Changed repo URL from SSH (`git@github.com:`) to HTTPS (`https://github.com/`).

This allows pip to install directly using `git+https://...` URLs without needing SSH key authentication. The dev-utils repo is public, so HTTPS works for all installations.

---

## File 2: installer.py

### Change 1: Remove `_transform_git_url_to_ssh()` function

**BEFORE** (lines ~188–208):
```python
def _transform_git_url_to_ssh(url: str) -> str:
    """
    Transform a git+https:// URL to bare SSH URL for pip install.

    GitHub URLs in HTTPS form need to be converted to SSH format that pip accepts.
    This function transforms:

        git+https://github.com/user/repo.git#subdirectory=path
    to:
        git+git@github.com:user/repo.git#subdirectory=path

    Args:
        url: A git+ URL string, potentially with HTTPS.

    Returns:
        The URL transformed to SSH format if it's a GitHub HTTPS URL,
        otherwise returned unchanged.
    """
    if "git+https://github.com/" in url:
        return url.replace(
            "git+https://github.com/",
            "git+git@github.com:"
        )
    return url
```

**AFTER:** Delete this entire function (lines 188–208).

### Change 2: Simplify `_run_pip_install()` function

**BEFORE** (lines ~210–238):
```python
def _run_pip_install(config: PluginConfig) -> None:
    """
    Run pip install for a plugin using the install URL from plugin config.

    Transforms HTTPS git URLs to SSH before passing to pip.

    Uses the same Python interpreter that is running setupkit to ensure
    the package is installed into the correct environment.

    Args:
        config: A validated PluginConfig instance.

    Raises:
        InstallError: If pip exits with a non-zero return code.
    """
    install_url = _transform_git_url_to_ssh(config.install.url)
    cmd = [sys.executable, "-m", "pip", "install", "-e", install_url]
    log.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        log.error("pip install failed for %s:\n%s", config.name, result.stderr)
        raise InstallError(
            f"pip install failed for {config.name} "
            f"(exit code {result.returncode}):\n{result.stderr}"
        )

    log.debug("pip output:\n%s", result.stdout)
```

**AFTER**:
```python
def _run_pip_install(config: PluginConfig) -> None:
    """
    Run pip install for a plugin using the install URL from plugin config.

    Uses the same Python interpreter that is running setupkit to ensure
    the package is installed into the correct environment.

    Args:
        config: A validated PluginConfig instance.

    Raises:
        InstallError: If pip exits with a non-zero return code.
    """
    install_url = config.install.url
    cmd = [sys.executable, "-m", "pip", "install", "-e", install_url]
    log.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        log.error("pip install failed for %s:\n%s", config.name, result.stderr)
        raise InstallError(
            f"pip install failed for {config.name} "
            f"(exit code {result.returncode}):\n{result.stderr}"
        )

    log.debug("pip output:\n%s", result.stdout)
```

### Change Explanation
- **Line 220 (now 216):** Remove the call to `_transform_git_url_to_ssh()`. Use `config.install.url` directly.
- **Docstring:** Remove the sentence "Transforms HTTPS git URLs to SSH before passing to pip." since we no longer do that.
- **Delete lines 188–208:** The entire `_transform_git_url_to_ssh()` function is no longer needed.

Pip now receives HTTPS URLs directly from the registry and handles them natively without transformation. This is the standard, supported approach for pip VCS installs.

---

## Why This Works

1. **HTTPS URLs are public-repo compatible**: Since `dev-utils` is public, no credentials needed.
2. **Pip supports `git+https://` natively**: No custom transformation required.
3. **Your SSH setup is unaffected**: Local git push still uses SSH keys; pip install uses HTTPS.
4. **No breaking changes**: The install UX stays the same—`setupkit install` still works.
