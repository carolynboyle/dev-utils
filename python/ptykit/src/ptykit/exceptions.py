"""
ptykit/exceptions.py

Exception hierarchy for ptykit.

All ptykit exceptions inherit from PtyKitError so callers can catch
the base class if they don't need to distinguish specific failures.

Exception hierarchy:
    PtyKitError
    ├── PtyKitConfigError   — config file missing, unreadable, or invalid
    ├── PtyKitPluginError   — plugin load or registration failure
    └── PtyKitWrapperError  — PTY spawn or IO failure
"""


class PtyKitError(Exception):
    """Base exception for all ptykit errors."""


class PtyKitConfigError(PtyKitError):
    """
    Raised when a config file is missing, unreadable, or fails validation.
    """


class PtyKitPluginError(PtyKitError):
    """
    Raised when a plugin cannot be loaded or registered.
    """


class PtyKitWrapperError(PtyKitError):
    """
    Raised when the PTY wrapper fails to spawn or communicate
    with the wrapped program.
    """
