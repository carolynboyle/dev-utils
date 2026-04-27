"""
viewkit.onthefly.exceptions - Exception hierarchy for the OTF query tool.

All OTF exceptions inherit from OTFError, allowing callers to catch
broadly or narrowly as needed.

Hierarchy:
    OTFError
    ├── OTFConfigError   — config file missing, unreadable, or malformed
    ├── OTFQueryError    — query file or definition invalid
    └── OTFRunError      — execution failure (connection, query, output)
"""


class OTFError(Exception):
    """Base exception for all OTF errors."""


class OTFConfigError(OTFError):
    """
    Raised when the OTF config is missing, unreadable, or malformed.

    Examples: config file not found, missing viewkit: section,
    missing required keys.
    """


class OTFQueryError(OTFError):
    """
    Raised when a query file or query definition is invalid.

    Examples: queries file not found, entity or query name not present,
    malformed query definition.
    """


class OTFRunError(OTFError):
    """
    Raised when query execution fails.

    Examples: database connection failure, SQL error, output write failure.
    """
