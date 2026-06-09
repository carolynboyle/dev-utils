
"""
packkit — Pack and ship server configuration archives.

Public API:
    load_config  — load and validate a packkit.yaml config file
    Packer       — orchestrates collection and archiving
    Collector    — collects files, directories, and command output
    Shipper      — transfers archives to a remote host
    RunLogger    — run logger and report writer

Exceptions:
    PackkitError            — base class for all packkit exceptions
    ConfigError             — base class for config exceptions
    ConfigNotFoundError     — config file not found
    ConfigParseError        — config file could not be parsed
    ConfigValidationError   — config file failed validation
    CollectorError          — base class for collector exceptions
    FileCollectionError     — file not found or unreadable
    DirectoryCollectionError — directory not found or unreadable
    CommandError            — command failed or timed out
    PackerError             — base class for packer exceptions
    StagingError            — staging directory could not be created
    ArchiveError            — tarball could not be created
    ShipperError            — base class for shipper exceptions
    ScpError                — scp transfer failed
    LogError                — log write failed
"""

from packkit.collector import Collector
from packkit.config import load_config
from packkit.exceptions import (
    ArchiveError,
    CollectorError,
    CommandError,
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    DirectoryCollectionError,
    FileCollectionError,
    LogError,
    PackerError,
    PackkitError,
    ScpError,
    ShipperError,
    StagingError,
)
from packkit.logger import RunLogger
from packkit.packer import Packer
from packkit.shipper import Shipper

__all__ = [
    'load_config',
    'Packer',
    'Collector',
    'Shipper',
    'RunLogger',
    'PackkitError',
    'ConfigError',
    'ConfigNotFoundError',
    'ConfigParseError',
    'ConfigValidationError',
    'CollectorError',
    'FileCollectionError',
    'DirectoryCollectionError',
    'CommandError',
    'PackerError',
    'StagingError',
    'ArchiveError',
    'ShipperError',
    'ScpError',
    'LogError',
]