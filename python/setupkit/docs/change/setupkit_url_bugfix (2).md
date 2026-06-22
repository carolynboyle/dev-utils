# setupkit URL Construction Bug Fixes

## Summary

Two bugs, two files.

**Bug 1** (`initialize.py`): The install URL was being generated with a `name @ url`
prefix, which pip rejects for editable (`-e`) installs. Editable installs require a
bare VCS URL.

**Bug 2** (`installer.py`): The SSH transform function was converting valid HTTPS URLs
to an invalid pip VCS scheme (`git+git@github.com:`), causing all installs to fail.

The registry `repo:` value was also corrected (in a prior commit) to remove the `.git`
suffix, which was causing double `.git` in install URLs and 404s on manifest fetches.

---

## File 1: `python/setupkit/src/setupkit/initialize.py`

### Change — Remove `name @` prefix from install URL

**Location:** `_init_from_registry()`, line 111

**BEFORE:**
```python
install_url = f"{name} @ git+{repo}.git#subdirectory={path}"
```

**AFTER:**
```python
install_url = f"git+{repo}.git#subdirectory={path}"
```

**Why:** Pip's `-e` (editable) flag does not accept the `name @ url` format. That
syntax is for non-editable installs only. The bare VCS URL is what pip expects:

```
# INVALID for editable install:
dbkit @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit

# CORRECT:
git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit
```

---

## File 2: `python/setupkit/src/setupkit/installer.py`

### Change 1 — Remove `_transform_git_url_to_ssh()` function

**BEFORE — delete this entire function:**
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

**AFTER:** Function deleted entirely.

---

### Change 2 — Update `_run_pip_install()` to use URL directly

**BEFORE:**
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

**AFTER:**
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

**Why:** The SSH transform was producing `git+git@github.com:` which is not a valid
pip VCS scheme. Since dev-utils is a public repo, HTTPS works without credentials
and pip handles it natively.

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
