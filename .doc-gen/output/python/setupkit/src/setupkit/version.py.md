# version.py

**Path:** python/setupkit/src/setupkit/version.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
setupkit.version - Version reading and comparison for setupkit.

Reads the currently installed version of a package using
importlib.metadata, and compares it against an upstream version
string using packaging.version for correct semantic version ordering.

Public API:
    get_installed_version  — get the installed version of a package by name
    parse_version          — parse a version string into a comparable object
    is_update_available    — compare installed vs upstream version
    VersionInfo            — dataclass summarising a version check result
"""

from dataclasses import dataclass
from importlib.metadata import version as get_package_version, PackageNotFoundError

from packaging.version import Version, InvalidVersion

from setupkit.exceptions import VersionError


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class VersionInfo:
    """
    Result of a version check between installed and upstream versions.

    Attributes:
        package:           Package name.
        installed:         Currently installed version string, or None if
                           the package is not installed.
        upstream:          Upstream version string from manifest.fletch,
                           or None if the manifest has no version field.
        update_available:  True if upstream is newer than installed.
        not_installed:     True if the package is not currently installed.
    """

    package: str
    installed: str | None
    upstream: str | None
    update_available: bool
    not_installed: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_installed_version(package_name: str) -> str | None:
    """
    Get the currently installed version of a package.

    Uses importlib.metadata to read the version from the installed
    package metadata. Works with both regular and editable installs.

    Args:
        package_name: The package name as declared in pyproject.toml
                      (e.g. 'dbkit', 'viewkit').

    Returns:
        Version string (e.g. '0.1.0'), or None if the package is not installed.
    """
    try:
        return get_package_version(package_name)
    except PackageNotFoundError:
        return None


def parse_version(version_string: str) -> Version:
    """
    Parse a version string into a comparable Version object.

    Args:
        version_string: A PEP 440 version string (e.g. '1.0.0', '0.2.1').

    Returns:
        A packaging.version.Version instance.

    Raises:
        VersionError: If the version string cannot be parsed.
    """
    try:
        return Version(version_string)
    except InvalidVersion as exc:
        raise VersionError(
            f"Could not parse version string {version_string!r}: {exc}"
        ) from exc


def is_update_available(
    package_name: str,
    upstream_version: str | None,
) -> VersionInfo:
    """
    Check whether an update is available for an installed package.

    Compares the currently installed version (read from importlib.metadata)
    against the upstream version from manifest.fletch.

    Args:
        package_name:     The package name as declared in pyproject.toml.
        upstream_version: Version string from manifest.fletch, or None if
                          the manifest has no version field.

    Returns:
        A VersionInfo dataclass summarising the result.

    Raises:
        VersionError: If either version string cannot be parsed.
    """
    installed_str = get_installed_version(package_name)
    not_installed = installed_str is None

    if not_installed or upstream_version is None:
        return VersionInfo(
            package=package_name,
            installed=installed_str,
            upstream=upstream_version,
            update_available=not_installed and upstream_version is not None,
            not_installed=not_installed,
        )

    installed_ver = parse_version(installed_str)
    upstream_ver = parse_version(upstream_version)

    return VersionInfo(
        package=package_name,
        installed=installed_str,
        upstream=upstream_version,
        update_available=upstream_ver > installed_ver,
        not_installed=False,
    )

```
