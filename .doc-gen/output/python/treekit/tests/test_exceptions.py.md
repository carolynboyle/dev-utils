# test_exceptions.py

**Path:** python/treekit/tests/test_exceptions.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
test_exceptions.py — Tests for the treekit exception hierarchy.

Covers:
    - All exceptions are subclasses of TreekitError
    - Parser exception hierarchy is correct
    - Builder exception hierarchy is correct
    - LogError hierarchy is correct
    - Exceptions can be raised and caught at every level of the hierarchy
    - Exception messages are preserved
"""

import pytest

from treekit.exceptions import (
    BuildError,
    EmptyInputError,
    LogError,
    NoTreeFoundError,
    OutputPathError,
    ParseError,
    PathCollisionError,
    TkPermissionError,
    TreekitError,
)


# -----------------------------------------------------------------------------
# Hierarchy — inheritance checks
# -----------------------------------------------------------------------------

class TestHierarchy:
    """All exceptions inherit correctly from their base classes."""

    # --- Parser exceptions ---------------------------------------------------

    def test_parse_error_is_treekit_error(self):
        assert issubclass(ParseError, TreekitError)

    def test_empty_input_error_is_parse_error(self):
        assert issubclass(EmptyInputError, ParseError)

    def test_empty_input_error_is_treekit_error(self):
        assert issubclass(EmptyInputError, TreekitError)

    def test_no_tree_found_error_is_parse_error(self):
        assert issubclass(NoTreeFoundError, ParseError)

    def test_no_tree_found_error_is_treekit_error(self):
        assert issubclass(NoTreeFoundError, TreekitError)

    # --- Builder exceptions --------------------------------------------------

    def test_build_error_is_treekit_error(self):
        assert issubclass(BuildError, TreekitError)

    def test_output_path_error_is_build_error(self):
        assert issubclass(OutputPathError, BuildError)

    def test_output_path_error_is_treekit_error(self):
        assert issubclass(OutputPathError, TreekitError)

    def test_path_collision_error_is_build_error(self):
        assert issubclass(PathCollisionError, BuildError)

    def test_path_collision_error_is_treekit_error(self):
        assert issubclass(PathCollisionError, TreekitError)

    def test_tk_permission_error_is_build_error(self):
        assert issubclass(TkPermissionError, BuildError)

    def test_tk_permission_error_is_treekit_error(self):
        assert issubclass(TkPermissionError, TreekitError)

    # --- Log exceptions ------------------------------------------------------

    def test_log_error_is_treekit_error(self):
        assert issubclass(LogError, TreekitError)


# -----------------------------------------------------------------------------
# Raise and catch — base class catching
# -----------------------------------------------------------------------------

class TestCatchAtBaseClass:
    """Specific exceptions can be caught at every level of the hierarchy."""

    def test_empty_input_caught_as_parse_error(self):
        with pytest.raises(ParseError):
            raise EmptyInputError("empty")

    def test_empty_input_caught_as_treekit_error(self):
        with pytest.raises(TreekitError):
            raise EmptyInputError("empty")

    def test_no_tree_found_caught_as_parse_error(self):
        with pytest.raises(ParseError):
            raise NoTreeFoundError("no tree")

    def test_no_tree_found_caught_as_treekit_error(self):
        with pytest.raises(TreekitError):
            raise NoTreeFoundError("no tree")

    def test_output_path_error_caught_as_build_error(self):
        with pytest.raises(BuildError):
            raise OutputPathError("bad path")

    def test_output_path_error_caught_as_treekit_error(self):
        with pytest.raises(TreekitError):
            raise OutputPathError("bad path")

    def test_path_collision_caught_as_build_error(self):
        with pytest.raises(BuildError):
            raise PathCollisionError("collision")

    def test_tk_permission_error_caught_as_build_error(self):
        with pytest.raises(BuildError):
            raise TkPermissionError("permission denied")

    def test_log_error_caught_as_treekit_error(self):
        with pytest.raises(TreekitError):
            raise LogError("log failed")


# -----------------------------------------------------------------------------
# Message preservation
# -----------------------------------------------------------------------------

class TestMessagePreservation:
    """Exception messages are accessible after raise."""

    def test_treekit_error_message(self):
        with pytest.raises(TreekitError) as exc_info:
            raise TreekitError("base error")
        assert "base error" in str(exc_info.value)

    def test_parse_error_message(self):
        with pytest.raises(ParseError) as exc_info:
            raise ParseError("malformed input")
        assert "malformed input" in str(exc_info.value)

    def test_empty_input_error_message(self):
        with pytest.raises(EmptyInputError) as exc_info:
            raise EmptyInputError("input is empty")
        assert "input is empty" in str(exc_info.value)

    def test_no_tree_found_error_message(self):
        with pytest.raises(NoTreeFoundError) as exc_info:
            raise NoTreeFoundError("no tree found")
        assert "no tree found" in str(exc_info.value)

    def test_build_error_message(self):
        with pytest.raises(BuildError) as exc_info:
            raise BuildError("build failed")
        assert "build failed" in str(exc_info.value)

    def test_output_path_error_message(self):
        with pytest.raises(OutputPathError) as exc_info:
            raise OutputPathError("path missing")
        assert "path missing" in str(exc_info.value)

    def test_path_collision_error_message(self):
        with pytest.raises(PathCollisionError) as exc_info:
            raise PathCollisionError("type mismatch at src/")
        assert "type mismatch at src/" in str(exc_info.value)

    def test_tk_permission_error_message(self):
        with pytest.raises(TkPermissionError) as exc_info:
            raise TkPermissionError("permission denied: /root/")
        assert "permission denied: /root/" in str(exc_info.value)

    def test_log_error_message(self):
        with pytest.raises(LogError) as exc_info:
            raise LogError("could not write log")
        assert "could not write log" in str(exc_info.value)

```
