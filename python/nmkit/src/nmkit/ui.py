"""
nmkit.ui - PySide6 main window and system tray for nmkit.

Displays a scrollable grid of connection cards. Each card shows a
Font Awesome OS-hint icon and the connection name. Double-clicking
a card (or single-clicking the Connect button) launches the NoMachine
session via the Launcher.

The system tray icon provides Show, Quit, and Force Quit options.
Closing the main window sends it to the tray rather than exiting.

Usage:
    from nmkit.config import ConfigManager
    from nmkit.launcher import Launcher
    from nmkit.ui import LauncherUI

    config   = ConfigManager()
    launcher = Launcher(config)

    app = LauncherUI(config, launcher)
    app.run()
"""

import logging
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QMenu,
    QGridLayout,
)

from nmkit.config import ConfigManager
from nmkit.exceptions import NmkitError
from nmkit.icons import connection_icon, tray_icon
from nmkit.launcher import Launcher

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CARD_WIDTH       = 120   # px — connection card width
_CARD_HEIGHT      = 140   # px — connection card height
_ICON_SIZE        = 64    # px — FA glyph icon
_GRID_COLUMNS     = 3     # cards per row in the grid
_GRID_SPACING     = 12    # px — spacing between cards
_WINDOW_MIN_W     = 420   # px
_WINDOW_MIN_H     = 300   # px


# ---------------------------------------------------------------------------
# ConnectionCard
# ---------------------------------------------------------------------------

class ConnectionCard(QFrame):  # pylint: disable=too-few-public-methods
    """
    A single connection card showing an OS-hint icon and the host name.

    Emits no signals — the parent grid wires up the click handler.

    Layout (top to bottom):
        [large FA glyph icon]
        [connection name label]
        [Connect button]
    """

    def __init__(self, connection: dict, launcher: Launcher, parent=None):
        """
        Initialise ConnectionCard.

        Args:
            connection: Connection dict with keys: name, host, port,
                        user, os.
            launcher:   Launcher instance — called on Connect.
            parent:     Optional Qt parent widget.
        """
        super().__init__(parent)
        self._connection = connection
        self._launcher   = launcher
        self._build()

    # -- Build ----------------------------------------------------------------

    def _build(self) -> None:
        """Construct the card layout."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedSize(_CARD_WIDTH, _CARD_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(4)

        # OS-hint icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        pixmap = connection_icon(self._connection.get("os", "unknown"), _ICON_SIZE)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        # Connection name
        name_label = QLabel(self._connection.get("name", "Unknown"))
        name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        name_label.setWordWrap(True)
        name_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(name_label)

        # Connect button
        btn = QPushButton("Connect")
        btn.clicked.connect(self._on_connect)  # pylint: disable=no-member
        layout.addWidget(btn)

    # -- Event handlers -------------------------------------------------------

    def _on_connect(self) -> None:
        """Handle Connect button click — launch the NoMachine session."""
        name = self._connection.get("name", "unknown")
        log.info("Connect requested for '%s'.", name)
        try:
            self._launcher.launch(self._connection)
        except NmkitError as exc:
            log.error("Launch failed for '%s': %s", name, exc)
            QMessageBox.critical(
                self,
                "Launch Failed",
                str(exc),
            )

    def mouseDoubleClickEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Double-click anywhere on the card also triggers Connect."""
        self._on_connect()
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# LauncherUI
# ---------------------------------------------------------------------------

class LauncherUI:  # pylint: disable=too-few-public-methods
    """
    nmkit main window and system tray.

    Builds a QMainWindow with a scrollable grid of ConnectionCard widgets.
    Closing the window sends it to the system tray. The tray provides
    Show, Quit, and Force Quit menu items.

    Usage:
        app = LauncherUI(config, launcher)
        app.run()
    """

    def __init__(self, config: ConfigManager, launcher: Launcher):
        """
        Initialise LauncherUI.

        Args:
            config:   Loaded ConfigManager instance.
            launcher: Launcher instance for launching sessions.
        """
        self._connections = config.connections
        self._launcher    = launcher
        self._title       = config.app.get("ui", {}).get("title", "NX Launcher")

        self._app    = QApplication.instance() or QApplication(sys.argv)
        self._window = QMainWindow()
        self._tray   = None

        self._build_window()
        self._build_tray()

    # -- Public interface -----------------------------------------------------

    def run(self) -> int:
        """
        Show the main window and start the Qt event loop.

        Returns:
            Exit code from QApplication.exec().
        """
        log.info("LauncherUI starting.")
        self._window.show()
        return self._app.exec()

    # -- Window ---------------------------------------------------------------

    def _build_window(self) -> None:
        """Construct the main window."""
        self._window.setWindowTitle(self._title)
        self._window.setMinimumSize(_WINDOW_MIN_W, _WINDOW_MIN_H)
        self._window.closeEvent = self._on_close

        central = QWidget()
        self._window.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        grid    = QGridLayout(content)
        grid.setSpacing(_GRID_SPACING)
        grid.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        for idx, conn in enumerate(self._connections):
            row = idx // _GRID_COLUMNS
            col = idx %  _GRID_COLUMNS
            card = ConnectionCard(conn, self._launcher)
            grid.addWidget(card, row, col)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # -- Tray -----------------------------------------------------------------

    def _build_tray(self) -> None:
        """Build the system tray icon and menu."""
        pixmap = tray_icon(22)
        icon   = QIcon(pixmap)

        self._tray = QSystemTrayIcon(icon, self._app)
        self._tray.setToolTip(self._title)

        menu = QMenu()
        show_action        = menu.addAction("Show")
        menu.addSeparator()
        quit_action        = menu.addAction("Quit")
        force_quit_action  = menu.addAction("Force Quit")

        show_action.triggered.connect(self._on_tray_show)
        quit_action.triggered.connect(self._on_tray_quit)
        force_quit_action.triggered.connect(self._on_tray_force_quit)

        self._tray.setContextMenu(menu)

        # Double-click tray icon also shows the window.
        self._tray.activated.connect(self._on_tray_activated)  # pylint: disable=no-member
        self._tray.show()

    # -- Event handlers -------------------------------------------------------

    def _on_close(self, event) -> None:
        """
        Intercept the window close event.

        Hides the window instead of quitting so the app lives in the tray.
        """
        event.ignore()
        self._window.hide()
        log.info("Window hidden to tray.")

    def _on_tray_show(self) -> None:
        """Restore and raise the main window."""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        log.info("Window restored from tray.")

    def _on_tray_quit(self) -> None:
        """Graceful quit — stops the Qt event loop."""
        log.info("Quit requested from tray.")
        self._tray.hide()
        self._app.quit()

    def _on_tray_force_quit(self) -> None:
        """
        Hard kill — bypasses any frozen event loop.

        Labeled Force Quit in the menu so the intent is clear.
        """
        log.warning("Force Quit requested from tray.")
        os._exit(0)  # pylint: disable=protected-access

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon activation.

        Double-clicking the tray icon shows the window.

        Args:
            reason: Qt activation reason enum value.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_tray_show()
