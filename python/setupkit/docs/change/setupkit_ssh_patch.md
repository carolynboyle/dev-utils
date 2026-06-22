# setupkit/installer.py patch

Add this function before `_run_pip_install()`:

```python
def _transform_git_url_to_ssh(url: str) -> str:
    """
    Transform a git+https:// URL to git+ssh:// for pip install.

    GitHub URLs in HTTPS form (from registry) need to be converted to SSH
    for authentication to work without credentials. This function transforms:

        git+https://github.com/user/repo.git#subdirectory=path
    to:
        git+ssh://git@github.com:user/repo.git#subdirectory=path

    Args:
        url: A git+ URL string, potentially with HTTPS.

    Returns:
        The URL transformed to SSH if it's a GitHub HTTPS URL,
        otherwise returned unchanged.
    """
    if "git+https://github.com/" in url:
        return url.replace(
            "git+https://github.com/",
            "git+ssh://git@github.com:"
        )
    return url
```

Then modify `_run_pip_install()`:

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
    install_url = _transform_git_url_to_ssh(config.install.url)  # <-- ADD THIS LINE
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

This way, the registry stays HTTPS (for raw manifest fetching), but pip gets SSH URLs (for authentication).
