"""
test_exceptions.py — Tests for the packkit exception hierarchy.

Covers:
    - All exceptions are subclasses of PackkitError
    - Each subsystem hierarchy is correct
    - Exceptions can be caught at every level
    - Exception messages are preserved
"""

import pytest

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


# -----------------------------------------------------------------------------
# Hierarchy — inheritance checks
# -----------------------------------------------------------------------------

class TestHierarchy:
    """All exceptions inherit correctly from their base classes."""

    # --- Config --------------------------------------------------------------

    def test_config_error_is_packkit_error(self):
        assert issubclass(ConfigError, PackkitError)

    def test_config_not_found_is_config_error(self):
        assert issubclass(ConfigNotFoundError, ConfigError)

    def test_config_not_found_is_packkit_error(self):
        assert issubclass(ConfigNotFoundError, PackkitError)

    def test_config_parse_error_is_config_error(self):
        assert issubclass(ConfigParseError, ConfigError)

    def test_config_validation_error_is_config_error(self):
        assert issubclass(ConfigValidationError, ConfigError)

    # --- Collector -----------------------------------------------------------

    def test_collector_error_is_packkit_error(self):
        assert issubclass(CollectorError, PackkitError)

    def test_file_collection_error_is_collector_error(self):
        assert issubclass(FileCollectionError, CollectorError)

    def test_file_collection_error_is_packkit_error(self):
        assert issubclass(FileCollectionError, PackkitError)

    def test_directory_collection_error_is_collector_error(self):
        assert issubclass(DirectoryCollectionError, CollectorError)

    def test_command_error_is_collector_error(self):
        assert issubclass(CommandError, CollectorError)

    # --- Packer --------------------------------------------------------------

    def test_packer_error_is_packkit_error(self):
        assert issubclass(PackerError, PackkitError)

    def test_staging_error_is_packer_error(self):
        assert issubclass(StagingError, PackerError)

    def test_archive_error_is_packer_error(self):
        assert issubclass(ArchiveError, PackerError)

    # --- Shipper -------------------------------------------------------------

    def test_shipper_error_is_packkit_error(self):
        assert issubclass(ShipperError, PackkitError)

    def test_scp_error_is_shipper_error(self):
        assert issubclass(ScpError, ShipperError)

    def test_scp_error_is_packkit_error(self):
        assert issubclass(ScpError, PackkitError)

    # --- Log -----------------------------------------------------------------

    def test_log_error_is_packkit_error(self):
        assert issubclass(LogError, PackkitError)


# -----------------------------------------------------------------------------
# Catch at base class
# -----------------------------------------------------------------------------

class TestCatchAtBaseClass:
    """Specific exceptions can be caught at every level of the hierarchy."""

    def test_config_not_found_caught_as_config_error(self):
        with pytest.raises(ConfigError):
            raise ConfigNotFoundError("not found")

    def test_config_not_found_caught_as_packkit_error(self):
        with pytest.raises(PackkitError):
            raise ConfigNotFoundError("not found")

    def test_file_collection_error_caught_as_collector_error(self):
        with pytest.raises(CollectorError):
            raise FileCollectionError("missing file")

    def test_command_error_caught_as_collector_error(self):
        with pytest.raises(CollectorError):
            raise CommandError("command failed")

    def test_staging_error_caught_as_packer_error(self):
        with pytest.raises(PackerError):
            raise StagingError("staging failed")

    def test_archive_error_caught_as_packer_error(self):
        with pytest.raises(PackerError):
            raise ArchiveError("tarball failed")

    def test_scp_error_caught_as_shipper_error(self):
        with pytest.raises(ShipperError):
            raise ScpError("scp failed")

    def test_log_error_caught_as_packkit_error(self):
        with pytest.raises(PackkitError):
            raise LogError("log failed")


# -----------------------------------------------------------------------------
# Message preservation
# -----------------------------------------------------------------------------

class TestMessagePreservation:
    """Exception messages are accessible after raise."""

    def test_config_not_found_message(self):
        with pytest.raises(ConfigNotFoundError) as exc_info:
            raise ConfigNotFoundError("packkit.yaml not found in /tmp")
        assert "packkit.yaml not found in /tmp" in str(exc_info.value)

    def test_file_collection_error_message(self):
        with pytest.raises(FileCollectionError) as exc_info:
            raise FileCollectionError("File not found: /etc/missing")
        assert "/etc/missing" in str(exc_info.value)

    def test_command_error_message(self):
        with pytest.raises(CommandError) as exc_info:
            raise CommandError("Command 'rpm -qa' failed (exit 127)")
        assert "rpm -qa" in str(exc_info.value)

    def test_scp_error_message(self):
        with pytest.raises(ScpError) as exc_info:
            raise ScpError("scp failed (exit 1): Connection refused")
        assert "Connection refused" in str(exc_info.value)
