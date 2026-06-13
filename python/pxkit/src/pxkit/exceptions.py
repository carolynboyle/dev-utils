"""
pxkit.exceptions - Exception classes for pxkit.
"""


class PxkitError(Exception):
    """Base exception for all pxkit errors."""


class PxkitConfigError(PxkitError):
    """Raised when a config file cannot be read or parsed."""


class PxkitConnectionError(PxkitError):
    """Raised when a Proxmox API call fails."""


class PxkitLaunchError(PxkitError):
    """Raised when a browser or remote-viewer launch fails."""
