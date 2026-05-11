# exceptions.py

**Path:** python/fletcher/fletcher/exceptions.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
fletcher.exceptions - Exception classes for the fletcher package

Part of the dev-utils toolkit / Project Crew.
Defines all custom exceptions raised by fletcher.

Exception hierarchy:
    FletcherError (base)
    ├── GitError
    │   └── GitBranchError
    ├── ManifestError
    │   ├── ManifestNotFoundError
    │   └── ManifestInvalidError
    └── ConfigError
        └── RepoConfigError
"""


class FletcherError(Exception):
    """Base exception for all fletcher errors."""
    pass


class GitError(FletcherError):
    """Raised when a git operation fails."""
    pass


class GitBranchError(GitError):
    """
    Raised when current branch cannot be detected.
    
    Common causes:
    - Not inside a git repository
    - Repository has no commits yet (empty HEAD)
    - git is not installed or not in PATH
    """
    pass


class ManifestError(FletcherError):
    """Raised when a manifest operation fails."""
    pass


class ManifestNotFoundError(ManifestError):
    """Raised when a required manifest file does not exist."""
    pass


class ManifestInvalidError(ManifestError):
    """
    Raised when a manifest file exists but is malformed or incomplete.
    
    Common causes:
    - Invalid YAML syntax
    - Missing required keys (e.g., 'documents')
    - Unreadable file (permission, encoding, etc.)
    """
    pass


class ConfigError(FletcherError):
    """Raised when a config operation fails."""
    pass


class RepoConfigError(ConfigError):
    """Raised when repository configuration is invalid or missing."""
    pass

```
