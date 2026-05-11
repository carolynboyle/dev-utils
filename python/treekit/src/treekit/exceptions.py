"""
exceptions.py — Exception hierarchy for treekit.

All treekit exceptions inherit from TreekitError so callers can catch
the base class when they don't need to distinguish between failure modes,
or catch specific subclasses when they do.
"""


class TreekitError(Exception):
    """Base class for all treekit exceptions."""


# --- Parser exceptions -------------------------------------------------------

class ParseError(TreekitError):
    """Raised when the markdown input cannot be parsed into a valid tree."""


class EmptyInputError(ParseError):
    """Raised when the input file or stdin contains no parseable tree content."""


class NoTreeFoundError(ParseError):
    """Raised when the input contains content but no recognisable tree structure."""


# --- Builder exceptions ------------------------------------------------------

class BuildError(TreekitError):
    """Raised when the filesystem tree cannot be created."""


class OutputPathError(BuildError):
    """Raised when the specified output path does not exist or is not a directory."""


class PathCollisionError(BuildError):
    """
    Raised when a path that should be a directory already exists as a file,
    or a path that should be a file already exists as a directory.
    """


class TkPermissionError(BuildError):
    """Raised when treekit lacks permission to create a path."""


# --- Log exceptions ----------------------------------------------------------

class LogError(TreekitError):
    """
    Raised when the run log cannot be written.

    Caught and reported as a warning — a log failure does not abort
    a successful tree creation.
    """
