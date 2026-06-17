"""
nmkit.icons - Icon generation for nmkit.

Generates QPixmap icons for connection cards and the system tray using
Font Awesome glyphs rendered with QPainter.

Card icons: a single large FA glyph in the OS hint colour, centred on
a transparent background. Simple and reliable at any size.

Systray icon: a monitor outline (fa-desktop) with the screen area
filled in NoMachine red.

Font files are loaded once via load_fonts(), which must be called after
QApplication is created and after assets.check() has confirmed the font
files are present.

Usage:
    from nmkit.icons import load_fonts, connection_icon, tray_icon

    load_fonts()                          # once, after QApplication()
    pixmap = connection_icon("rocky", 64) # per connection card
    tray   = tray_icon(22)               # for QSystemTrayIcon
"""

import logging

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QPixmap,
)

from nmkit.assets import fonts
from nmkit.exceptions import NmkitAssetError

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# NoMachine brand red — used for systray screen fill.
# ---------------------------------------------------------------------------

_NM_RED = "#d52b1e"


# ---------------------------------------------------------------------------
# OS hint registry
# ---------------------------------------------------------------------------
# Each entry: (unicode_glyph, hex_color, font_style)
# font_style must be one of: 'solid', 'brands', 'regular'
#
# Glyph codepoints (Font Awesome 6 Free):
#   fa-linux    \uf17c  (brands)
#   fa-windows  \uf17a  (brands)
#   fa-apple    \uf179  (brands)
#   fa-desktop  \uf108  (solid)  — used as fallback and systray

_OS_HINTS: dict[str, tuple[str, str, str]] = {
    "debian":   ("\uf17c", "#d70a53", "brands"),  # Linux glyph, Debian red
    "ubuntu":   ("\uf17c", "#e95420", "brands"),  # Linux glyph, Ubuntu orange
    "rocky":    ("\uf17c", "#10b981", "brands"),  # Linux glyph, Rocky green
    "rhel":     ("\uf17c", "#cc0000", "brands"),  # Linux glyph, RHEL red
    "fedora":   ("\uf17c", "#3c6eb4", "brands"),  # Linux glyph, Fedora blue
    "opensuse": ("\uf17c", "#73ba25", "brands"),  # Linux glyph, openSUSE green
    "arch":     ("\uf17c", "#1793d1", "brands"),  # Linux glyph, Arch blue
    "windows":  ("\uf17a", "#00a4ef", "brands"),  # Windows glyph, MS blue
    "macos":    ("\uf179", "#555555", "brands"),  # Apple glyph, grey
    "unknown":  ("\uf108", "#888888", "solid"),   # Desktop glyph, grey
}

_FALLBACK_HINT = _OS_HINTS["unknown"]


# ---------------------------------------------------------------------------
# Font registry — populated by load_fonts()
# ---------------------------------------------------------------------------

_font_families: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def load_fonts() -> None:
    """
    Register Font Awesome .ttf files with Qt's font database.

    Must be called once after QApplication is created and after
    assets.check() has confirmed the font files are present.

    Raises:
        NmkitAssetError: If font files are missing or fail to load.
    """
    font_paths = fonts()

    for style, path in font_paths.items():
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id == -1:
            raise NmkitAssetError(
                f"Qt failed to load font file: {path}"
            )
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            raise NmkitAssetError(
                f"No font families found in: {path}"
            )
        _font_families[style] = families[0]
        log.debug("Loaded font '%s' from %s", families[0], path)


def connection_icon(os_hint: str, size: int = 64) -> QPixmap:
    """
    Generate a square icon for a connection card.

    Renders a single large FA glyph centred on a transparent background
    in the OS hint colour. If os_hint is unrecognised, renders the
    generic desktop glyph in grey.

    Args:
        os_hint: OS identifier string (e.g. 'rocky', 'debian').
                 Unknown values render as 'unknown'.
        size:    Icon width and height in pixels. Default 64.

    Returns:
        QPixmap of the requested size.
    """
    glyph, color, style = _OS_HINTS.get(os_hint.lower(), _FALLBACK_HINT)
    return _render_glyph(size, glyph, QColor(color), style)


def tray_icon(size: int = 22) -> QPixmap:
    """
    Generate the system tray icon.

    Renders the fa-desktop monitor outline with the screen area filled
    in NoMachine red.

    Args:
        size: Icon width and height in pixels. Default 22.

    Returns:
        QPixmap of the requested size.
    """
    return _render_tray(size)


def os_hints() -> list[str]:
    """
    Return the list of supported OS hint strings.

    Returns:
        Sorted list of valid os hint values.
    """
    return sorted(_OS_HINTS.keys())


# ---------------------------------------------------------------------------
# Internal rendering
# ---------------------------------------------------------------------------

def _render_glyph(
    size: int,
    glyph: str,
    color: QColor,
    font_style: str,
) -> QPixmap:
    """
    Render a single FA glyph centred on a transparent pixmap.

    Args:
        size:       Width and height of the output pixmap in pixels.
        glyph:      Unicode character to render.
        color:      Glyph colour.
        font_style: Font style key: 'solid', 'brands', or 'regular'.

    Returns:
        QPixmap of the requested size.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    painter.setFont(_make_font(font_style, int(size * 0.80)))
    painter.setPen(color)
    painter.drawText(
        pixmap.rect(),
        Qt.AlignmentFlag.AlignCenter,
        glyph,
    )

    painter.end()
    return pixmap


def _render_tray(size: int) -> QPixmap:
    """
    Render the systray icon: fa-desktop outline with red screen fill.

    The screen rect ratios are tuned for the FA 6 desktop glyph and
    should hold reasonably well across small sizes (16-32px). Adjust
    the ratios in _screen_rect() if the fill looks misaligned.

    Args:
        size: Width and height of the output pixmap in pixels.

    Returns:
        QPixmap of the requested size.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Monitor outline
    painter.setFont(_make_font("solid", int(size * 0.85)))
    painter.setPen(QColor("#cccccc"))
    painter.drawText(
        pixmap.rect(),
        Qt.AlignmentFlag.AlignCenter,
        "\uf108",  # fa-desktop
    )

    # Screen fill
    left   = int(size * 0.18)
    top    = int(size * 0.08)
    width  = int(size * 0.64)
    height = int(size * 0.50)
    painter.fillRect(QRect(left, top, width, height), QColor(_NM_RED))

    painter.end()
    return pixmap


def _make_font(style: str, pixel_size: int) -> QFont:
    """
    Create a QFont for the given Font Awesome style at the given size.

    Falls back to monospace if the FA family is not loaded, to avoid
    a hard crash during testing before load_fonts() is called.

    Args:
        style:      Font style key: 'solid', 'brands', or 'regular'.
        pixel_size: Font size in pixels.

    Returns:
        QFont configured for the requested style and size.
    """
    family = _font_families.get(style, "monospace")
    font   = QFont(family)
    font.setPixelSize(pixel_size)
    return font
