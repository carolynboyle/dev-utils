"""
nmkit.exceptions - Exception classes for nmkit.
"""


class NmkitError(Exception):
    """Base exception for all nmkit errors."""


class NmkitConfigError(NmkitError):
    """Raised when a config file cannot be read or parsed."""


class NmkitAssetError(NmkitError):
    """Raised when a required asset file is missing and download is declined."""


class NmkitLaunchError(NmkitError):
    """Raised when an nxclient launch fails."""
