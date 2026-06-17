"""
tests/test_icons.py - Tests for nmkit.icons.

Covers the OS hint registry, font loading, and icon generation.
Qt rendering is not tested (requires a display) — tests focus on
the registry data, fallback behaviour, and the public API surface.
QPixmap rendering tests are skipped when no display is available.
"""

import pytest

from nmkit.icons import (
    _OS_HINTS,
    _FALLBACK_HINT,
    _NM_RED,
    os_hints,
)


# ---------------------------------------------------------------------------
# OS hint registry
# ---------------------------------------------------------------------------

class TestOsHintRegistry:

    def test_registry_is_not_empty(self):
        """_OS_HINTS contains at least one entry."""
        assert len(_OS_HINTS) > 0

    def test_all_entries_have_three_elements(self):
        """Every entry in _OS_HINTS is a 3-tuple."""
        for key, value in _OS_HINTS.items():
            assert len(value) == 3, f"Entry for '{key}' does not have 3 elements"

    def test_all_glyphs_are_strings(self):
        """Every glyph in _OS_HINTS is a non-empty string."""
        for key, (glyph, _, _) in _OS_HINTS.items():
            assert isinstance(glyph, str) and glyph, f"Glyph for '{key}' is empty"

    def test_all_colors_are_hex(self):
        """Every color in _OS_HINTS is a valid hex color string."""
        for key, (_, color, _) in _OS_HINTS.items():
            assert color.startswith("#"), f"Color for '{key}' is not a hex string"
            assert len(color) == 7, f"Color for '{key}' is not #RRGGBB format"

    def test_all_font_styles_are_valid(self):
        """Every font style in _OS_HINTS is one of solid, brands, regular."""
        valid_styles = {"solid", "brands", "regular"}
        for key, (_, _, style) in _OS_HINTS.items():
            assert style in valid_styles, (
                f"Font style for '{key}' is '{style}', expected one of {valid_styles}"
            )

    def test_unknown_key_in_registry(self):
        """'unknown' is present in _OS_HINTS as the fallback."""
        assert "unknown" in _OS_HINTS

    def test_fallback_hint_matches_unknown(self):
        """_FALLBACK_HINT matches the 'unknown' entry in _OS_HINTS."""
        assert _FALLBACK_HINT == _OS_HINTS["unknown"]

    def test_expected_os_keys_present(self):
        """Expected OS hint keys are all present in the registry."""
        expected = {
            "debian", "ubuntu", "rocky", "rhel", "fedora",
            "opensuse", "arch", "windows", "macos", "unknown",
        }
        for key in expected:
            assert key in _OS_HINTS, f"'{key}' missing from _OS_HINTS"

    def test_nm_red_is_hex_color(self):
        """_NM_RED is a valid hex color string."""
        assert _NM_RED.startswith("#")
        assert len(_NM_RED) == 7


# ---------------------------------------------------------------------------
# os_hints()
# ---------------------------------------------------------------------------

class TestOsHints:

    def test_returns_list(self):
        """os_hints() returns a list."""
        assert isinstance(os_hints(), list)

    def test_returns_sorted_list(self):
        """os_hints() returns a sorted list."""
        result = os_hints()
        assert result == sorted(result)

    def test_contains_all_registry_keys(self):
        """os_hints() contains all keys from _OS_HINTS."""
        assert set(os_hints()) == set(_OS_HINTS.keys())

    def test_contains_unknown(self):
        """os_hints() includes 'unknown'."""
        assert "unknown" in os_hints()


# ---------------------------------------------------------------------------
# load_fonts() and rendering — skipped without display
# ---------------------------------------------------------------------------

class TestLoadFonts:

    def test_load_fonts_requires_qapplication(self):
        """
        load_fonts() requires a QApplication to exist first.

        This test verifies the import works and the function exists.
        Actual font loading is an integration concern tested manually.
        """
        from nmkit.icons import load_fonts
        assert callable(load_fonts)

    def test_connection_icon_function_exists(self):
        """connection_icon() is importable and callable."""
        from nmkit.icons import connection_icon
        assert callable(connection_icon)

    def test_tray_icon_function_exists(self):
        """tray_icon() is importable and callable."""
        from nmkit.icons import tray_icon
        assert callable(tray_icon)


# ---------------------------------------------------------------------------
# Rendering — skipped without display
# ---------------------------------------------------------------------------

try:
    from PySide6.QtWidgets import QApplication
    import sys
    _app = QApplication.instance() or QApplication(sys.argv)
    _HAS_DISPLAY = True
except Exception:  # pylint: disable=broad-except
    _HAS_DISPLAY = False


@pytest.mark.skipif(not _HAS_DISPLAY, reason="No display available")
class TestIconRendering:

    def test_connection_icon_returns_pixmap(self):
        """connection_icon() returns a non-null QPixmap."""
        from PySide6.QtGui import QPixmap
        from nmkit.icons import connection_icon
        pixmap = connection_icon("rocky", 64)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()

    def test_connection_icon_correct_size(self):
        """connection_icon() returns a pixmap of the requested size."""
        from nmkit.icons import connection_icon
        pixmap = connection_icon("debian", 48)
        assert pixmap.width()  == 48
        assert pixmap.height() == 48

    def test_connection_icon_unknown_os_does_not_raise(self):
        """connection_icon() with unknown os hint does not raise."""
        from nmkit.icons import connection_icon
        pixmap = connection_icon("haiku", 64)
        assert not pixmap.isNull()

    def test_tray_icon_returns_pixmap(self):
        """tray_icon() returns a non-null QPixmap."""
        from PySide6.QtGui import QPixmap
        from nmkit.icons import tray_icon
        pixmap = tray_icon(22)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()

    def test_tray_icon_correct_size(self):
        """tray_icon() returns a pixmap of the requested size."""
        from nmkit.icons import tray_icon
        pixmap = tray_icon(22)
        assert pixmap.width()  == 22
        assert pixmap.height() == 22
