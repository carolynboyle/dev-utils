# setupkit URL Construction Bug Fixes

## Summary

Two bugs, two files. Both caused by the registry `repo:` value including a `.git`
suffix that the URL-building code wasn't expecting.

The simplest fix is to remove `.git` from the registry — it's the single source of
truth, and a clean base URL works everywhere without any code-side stripping.

The second fix removes the SSH transform from `installer.py` that was missed in the
previous commit.

---

## File 1: `python/setupkit/setupkit-registry.yaml`

**BEFORE:**
```yaml
repo: https://github.com/carolynboyle/dev-utils.git
```

**AFTER:**
```yaml
repo: https://github.com/carolynboyle/dev-utils
```

**Why:** The registry is the single source of truth for the repo URL. Storing a
clean base URL means `_init_from_registry()` can build manifest and install URLs
directly without stripping or transforming anything:

- Manifest URL: `{repo}/raw/{branch}/{manifest_path}` → correct as-is
- Install URL: `{name} @ git+{repo}.git#subdirectory={path}` → appends `.git` once, correctly

No changes needed in `initialize.py`.

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
