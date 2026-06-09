"""
exceptions.py — Exception hierarchy for pack-kit.

All packkit exceptions inherit from PackkitError so callers can catch
the base class when they don't need to distinguish between failure modes,
or catch specific subclasses when they do.
"""


class PackkitError(Exception):
    """Base class for all packkit exceptions."""


# --- Config exceptions -------------------------------------------------------

class ConfigError(PackkitError):
    """Raised when the pack-kit configuration cannot be loaded or is invalid."""


class ConfigNotFoundError(ConfigError):
    """Raised when no packkit.yaml is found in the current directory or at the specified path."""


class ConfigParseError(ConfigError):
    """Raised when the config file cannot be parsed as valid YAML."""


class ConfigValidationError(ConfigError):
    """Raised when the config file is valid YAML but fails structural validation."""


# --- Collector exceptions ----------------------------------------------------

class CollectorError(PackkitError):
    """Raised when a file, directory, or command collection step fails."""


class FileCollectionError(CollectorError):
    """Raised when a specified file cannot be found or read."""


class DirectoryCollectionError(CollectorError):
    """Raised when a specified directory cannot be found or copied."""


class CommandError(CollectorError):
    """Raised when a command returns a non-zero exit code or cannot be executed."""


# --- Packer exceptions -------------------------------------------------------

class PackerError(PackkitError):
    """Raised when the staging directory or tarball cannot be created."""


class StagingError(PackerError):
    """Raised when the staging directory cannot be created or written to."""


class ArchiveError(PackerError):
    """Raised when the tarball cannot be created."""


# --- Shipper exceptions ------------------------------------------------------

class ShipperError(PackkitError):
    """Raised when the archive cannot be transferred to the remote host."""


class ScpError(ShipperError):
    """Raised when the scp transfer fails or the remote host is unreachable."""


# --- Log exceptions ----------------------------------------------------------

class LogError(PackkitError):
    """
    Raised when the run log cannot be written.

    The log is also the run report — a log failure is always fatal.
    """