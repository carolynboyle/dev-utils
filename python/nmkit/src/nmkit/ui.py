"""
nmkit.ui - PySide6 main window and system tray for nmkit.

Displays a scrollable grid of connection cards. Each card shows a
Font Awesome OS-hint icon and the connection name. Clicking a card
selects it; double-clicking or clicking Connect launches the session.

A toolbar above the grid provides Add, Edit, and Delete buttons.
Edit and Delete are enabled only when a card is selected.

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
    QHBoxLayout,
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
from nmkit.connection_dialog import ConnectionDialog
from nmkit.exceptions import NmkitError, NmkitConfigError
from nmkit.icons import connection_icon, tray_icon
from nmkit.launcher import Launcher

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CARD_WIDTH    = 120   # px — connection card width
_CARD_HEIGHT   = 140   # px — connection card height
_ICON_SIZE     = 64    # px — FA glyph icon
_GRID_COLUMNS  = 3     # cards per row in the grid
_GRID_SPACING  = 12    # px — spacing between cards
_WINDOW_MIN_W  = 420   # px
_WINDOW_MIN_H  = 300   # px

# Stylesheet for selected card highlight.
_CARD_SELECTED_STYLE   = "QFrame { border: 2px solid #d52b1e; background: #2a2a2a; }"
_CARD_UNSELECTED_STYLE = ""


# ---------------------------------------------------------------------------
# ConnectionCard
# ---------------------------------------------------------------------------

class ConnectionCard(QFrame):  # pylint: disable=too-few-public-methods
    """
    A single connection card showing an OS-hint icon and the host name.

    Supports click-to-select (highlighted border) and notifies a parent
    callback when selected. Double-clicking triggers Connect.

    Layout (top to bottom):
        [large FA glyph icon]
        [connection name label]
        [Connect button]
    """

    def __init__(
        self,
        connection: dict,
        launcher: Launcher,
        on_select,
        parent=None,
    ):
        """
        Initialise ConnectionCard.

        Args:
            connection: Connection dict with keys: name, host, port,
                        user, os.
            launcher:   Launcher instance — called on Connect.
            on_select:  Callable(ConnectionCard) — called when this card
                        is clicked to notify the parent of selection.
            parent:     Optional Qt parent widget.
        """
        super().__init__(parent)
        self._connection = connection
        self._launcher   = launcher
        self._on_select  = on_select
        self._selected   = False
        self._build()

    @property
    def connection(self) -> dict:
        """Return the connection dict for this card."""
        return self._connection

    def set_selected(self, selected: bool) -> None:
        """
        Set the visual selected state of this card.

        Args:
            selected: True to highlight, False to clear.
        """
        self._selected = selected
        self.setStyleSheet(
            _CARD_SELECTED_STYLE if selected else _CARD_UNSELECTED_STYLE
        )

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

    def mousePressEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Single click selects this card."""
        self._on_select(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Double-click triggers Connect."""
        self._on_connect()
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# LauncherUI
# ---------------------------------------------------------------------------

class LauncherUI:  # pylint: disable=too-few-public-methods
    """
    nmkit main window and system tray.

    Builds a QMainWindow with a toolbar and a scrollable grid of
    ConnectionCard widgets. Closing the window sends it to the system
    tray. The tray provides Show, Quit, and Force Quit menu items.

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
        self._config   = config
        self._launcher = launcher
        self._title    = config.app.get("ui", {}).get("title", "NX Launcher")

        self._app           = QApplication.instance() or QApplication(sys.argv)
        self._window        = QMainWindow()
        self._tray          = None
        self._grid          = None
        self._grid_content  = None
        self._selected_card = None
        self._edit_btn      = None
        self._delete_btn    = None
        self._cards         = []

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
        """Construct the main window with toolbar and card grid."""
        self._window.setWindowTitle(self._title)
        self._window.setMinimumSize(_WINDOW_MIN_W, _WINDOW_MIN_H)
        self._window.closeEvent = self._on_close

        central = QWidget()
        self._window.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # Toolbar
        toolbar = self._build_toolbar()
        outer.addLayout(toolbar)

        # Scrollable card grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_content = QWidget()
        self._grid         = QGridLayout(self._grid_content)
        self._grid.setSpacing(_GRID_SPACING)
        self._grid.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        scroll.setWidget(self._grid_content)
        outer.addWidget(scroll)

        # Click on empty area deselects
        self._grid_content.mousePressEvent = self._on_background_click

        self._populate_grid(self._config.connections)

    def _build_toolbar(self) -> QHBoxLayout:
        """
        Build the Add / Edit / Delete toolbar.

        Returns:
            QHBoxLayout containing the toolbar buttons.
        """
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        add_btn    = QPushButton("Add")
        edit_btn   = QPushButton("Edit")
        delete_btn = QPushButton("Delete")

        edit_btn.setEnabled(False)
        delete_btn.setEnabled(False)

        add_btn.clicked.connect(self._on_add)       # pylint: disable=no-member
        edit_btn.clicked.connect(self._on_edit)     # pylint: disable=no-member
        delete_btn.clicked.connect(self._on_delete) # pylint: disable=no-member

        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addStretch()

        self._edit_btn   = edit_btn
        self._delete_btn = delete_btn

        return toolbar

    def _populate_grid(self, connections: list) -> None:
        """
        Populate the card grid from a connection list.

        Clears any existing cards first.

        Args:
            connections: List of connection dicts.
        """
        # Clear existing cards
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards         = []
        self._selected_card = None
        self._update_toolbar_buttons()

        for idx, conn in enumerate(connections):
            row  = idx // _GRID_COLUMNS
            col  = idx %  _GRID_COLUMNS
            card = ConnectionCard(conn, self._launcher, self._on_card_select)
            self._grid.addWidget(card, row, col)
            self._cards.append(card)

    # -- Toolbar handlers -----------------------------------------------------

    def _on_add(self) -> None:
        """Open the Add Connection dialog and save on accept."""
        dialog = ConnectionDialog(parent=self._window)
        if dialog.exec():
            connection  = dialog.get_connection()
            connections = list(self._config.connections) + [connection]
            self._save_and_refresh(connections)
            log.info("Added connection '%s'.", connection["name"])

    def _on_edit(self) -> None:
        """Open the Edit Connection dialog pre-populated and save on accept."""
        if not self._selected_card:
            return
        existing = self._selected_card.connection
        dialog   = ConnectionDialog(connection=existing, parent=self._window)
        if dialog.exec():
            updated     = dialog.get_connection()
            connections = [
                updated if c["name"] == existing["name"] else c
                for c in self._config.connections
            ]
            self._save_and_refresh(connections)
            log.info("Edited connection '%s'.", updated["name"])

    def _on_delete(self) -> None:
        """Confirm and delete the selected connection."""
        if not self._selected_card:
            return
        name   = self._selected_card.connection.get("name", "this connection")
        result = QMessageBox.question(
            self._window,
            "Delete Connection",
            f"Delete '{name}'?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Ok:
            connections = [
                c for c in self._config.connections
                if c["name"] != name
            ]
            self._save_and_refresh(connections)
            log.info("Deleted connection '%s'.", name)

    def _save_and_refresh(self, connections: list) -> None:
        """
        Save a connection list to disk and refresh the grid.

        Args:
            connections: Updated list of connection dicts.
        """
        try:
            self._config.save_connections(connections)
        except NmkitConfigError as exc:
            log.error("Failed to save connections: %s", exc)
            QMessageBox.critical(
                self._window,
                "Save Failed",
                str(exc),
            )
            return
        self._populate_grid(self._config.connections)

    # -- Card selection -------------------------------------------------------

    def _on_card_select(self, card: ConnectionCard) -> None:
        """
        Handle card selection — highlight selected, clear others.

        Args:
            card: The card that was clicked.
        """
        if self._selected_card and self._selected_card is not card:
            self._selected_card.set_selected(False)
        self._selected_card = card
        card.set_selected(True)
        self._update_toolbar_buttons()

    def _on_background_click(self, event) -> None:
        """Clicking empty grid background deselects the current card."""
        if self._selected_card:
            self._selected_card.set_selected(False)
            self._selected_card = None
            self._update_toolbar_buttons()
        QWidget.mousePressEvent(self._grid_content, event)

    def _update_toolbar_buttons(self) -> None:
        """Enable Edit and Delete only when a card is selected."""
        has_selection = self._selected_card is not None
        if self._edit_btn:
            self._edit_btn.setEnabled(has_selection)
        if self._delete_btn:
            self._delete_btn.setEnabled(has_selection)

    # -- Tray -----------------------------------------------------------------

    def _build_tray(self) -> None:
        """Build the system tray icon and menu."""
        pixmap = tray_icon(22)
        icon   = QIcon(pixmap)

        self._tray = QSystemTrayIcon(icon, self._app)
        self._tray.setToolTip(self._title)

        menu = QMenu()
        show_action       = menu.addAction("Show")
        menu.addSeparator()
        quit_action       = menu.addAction("Quit")
        force_quit_action = menu.addAction("Force Quit")

        show_action.triggered.connect(self._on_tray_show)           # pylint: disable=no-member
        quit_action.triggered.connect(self._on_tray_quit)           # pylint: disable=no-member
        force_quit_action.triggered.connect(self._on_tray_force_quit)  # pylint: disable=no-member

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)       # pylint: disable=no-member
        self._tray.show()

    # -- Event handlers -------------------------------------------------------

    def _on_close(self, event) -> None:
        """Hide window to tray instead of quitting."""
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
        """Graceful quit."""
        log.info("Quit requested from tray.")
        self._tray.hide()
        self._app.quit()

    def _on_tray_force_quit(self) -> None:
        """Hard kill — bypasses any frozen event loop."""
        log.warning("Force Quit requested from tray.")
        os._exit(0)  # pylint: disable=protected-access

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        """Double-click tray icon shows the window."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_tray_show()
