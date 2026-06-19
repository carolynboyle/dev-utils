"""
nmkit.ui - PySide6 main window and system tray for nmkit.

Wraps the Qt Designer generated Ui_NMConnect from nmLauncher_ui.py.
Populates the connection list from config, handles selection, and
wires up Add/Edit/Delete/Connect buttons.

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

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from nmkit.config import ConfigManager
from nmkit.connection_dialog import ConnectionDialog
from nmkit.exceptions import NmkitError, NmkitConfigError
from nmkit.icons import connection_icon, tray_icon
from nmkit.launcher import Launcher
from nmkit.nmLauncher_ui import Ui_NMConnect

log = logging.getLogger("nmkit")

_ICON_SIZE   = 48   # px — list item icon size
_MIN_WIDTH   = 500  # px — minimum window width
_MIN_HEIGHT  = 400  # px — minimum window height


# ---------------------------------------------------------------------------
# LauncherUI
# ---------------------------------------------------------------------------

class LauncherUI:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """
    nmkit main window and system tray.

    Wraps Ui_NMConnect — the Qt Designer layout. Replaces the QListView
    from the .ui file with a QListWidget for simpler item management.
    Populates the list from config on startup and after any change.

    Usage:
        app = LauncherUI(config, launcher)
        app.run()
    """

    def __init__(self, config: ConfigManager, launcher: Launcher):
        self._config   = config
        self._launcher = launcher
        self._title    = config.app.get("ui", {}).get("title", "NX Launcher")

        self._app    = QApplication.instance() or QApplication(sys.argv)
        self._window = QMainWindow()
        self._tray   = None

        # Central widget using the Designer layout
        self._central = QDialog()
        self._ui      = Ui_NMConnect()
        self._ui.setupUi(self._central)

        # Replace QListView with QListWidget in the same geometry
        self._list = QListWidget(self._central)
        self._list.setGeometry(self._ui.connections_list.geometry())
        self._list.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self._ui.connections_list.hide()

        self._window.setWindowTitle(self._title)
        self._window.setCentralWidget(self._central)
        self._window.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self._window.closeEvent = self._on_close

        self._setup_list()
        self._wire_buttons()
        self._wire_list()
        self._update_buttons(False)
        self._build_tray()

    # -- Public interface -----------------------------------------------------

    def run(self) -> int:
        """Show the main window and start the Qt event loop."""
        log.info("LauncherUI starting.")
        self._window.show()
        self._window.adjustSize()
        return self._app.exec()

    # -- List -----------------------------------------------------------------

    def _setup_list(self) -> None:
        """Populate the list widget from the current config."""
        self._list.clear()
        self._ui.conn_name.setText("")
        self._ui.conn_description.setText("")

        for conn in self._config.connections:
            item = QListWidgetItem()
            item.setText(conn.get("name", "Unknown"))
            item.setIcon(
                QIcon(connection_icon(conn.get("os", "unknown"), _ICON_SIZE))
            )
            item.setData(Qt.ItemDataRole.UserRole, conn)
            self._list.addItem(item)

    def _wire_list(self) -> None:
        """Connect list signals."""
        self._list.itemClicked.connect(self._on_item_clicked)          # pylint: disable=no-member
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)  # pylint: disable=no-member
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_right_click)  # pylint: disable=no-member

    def _wire_buttons(self) -> None:
        """Connect toolbar button signals."""
        self._ui.add_connection.clicked.connect(self._on_add)       # pylint: disable=no-member
        self._ui.edit_connection.clicked.connect(self._on_edit)     # pylint: disable=no-member
        self._ui.delete_connection.clicked.connect(self._on_delete) # pylint: disable=no-member
        self._ui.connect.clicked.connect(self._on_connect)          # pylint: disable=no-member

    def _update_buttons(self, has_selection: bool) -> None:
        """Enable/disable buttons based on selection state."""
        self._ui.edit_connection.setEnabled(has_selection)
        self._ui.delete_connection.setEnabled(has_selection)
        self._ui.connect.setEnabled(has_selection)

    def _selected_connection(self) -> dict | None:
        """Return the connection dict for the currently selected item."""
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    # -- List event handlers --------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Single click — update selection display and enable buttons."""
        conn = item.data(Qt.ItemDataRole.UserRole)
        self._ui.conn_name.setText(conn.get("name", ""))
        self._ui.conn_description.setText(conn.get("description", ""))
        self._update_buttons(True)
        log.debug("Selected connection '%s'.", conn.get("name"))

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Double click — connect immediately."""
        self._on_item_clicked(item)
        self._on_connect()

    def _on_right_click(self, pos) -> None:
        """Right click — show context menu."""
        if not self._list.itemAt(pos):
            return

        menu = QMenu(self._central)
        act_connect = QAction("Connect",      self._central)
        act_view    = QAction("View Details", self._central)
        act_edit    = QAction("Edit",         self._central)
        act_delete  = QAction("Delete",       self._central)

        act_connect.triggered.connect(self._on_connect)      # pylint: disable=no-member
        act_view.triggered.connect(self._on_view_details)    # pylint: disable=no-member
        act_edit.triggered.connect(self._on_edit)            # pylint: disable=no-member
        act_delete.triggered.connect(self._on_delete)        # pylint: disable=no-member

        menu.addAction(act_connect)
        menu.addSeparator()
        menu.addAction(act_view)
        menu.addAction(act_edit)
        menu.addAction(act_delete)

        menu.exec(self._list.mapToGlobal(pos))

    # -- Button handlers ------------------------------------------------------

    def _on_add(self) -> None:
        """Open Add Connection dialog."""
        dialog = ConnectionDialog(parent=self._central)
        if dialog.exec():
            conn        = dialog.get_connection()
            connections = list(self._config.connections) + [conn]
            self._save_and_refresh(connections)
            log.info("Added connection '%s'.", conn["name"])

    def _on_edit(self) -> None:
        """Open Edit Connection dialog pre-populated."""
        conn = self._selected_connection()
        if not conn:
            return
        dialog = ConnectionDialog(connection=conn, parent=self._central)
        if dialog.exec():
            updated     = dialog.get_connection()
            connections = [
                updated if c["name"] == conn["name"] else c
                for c in self._config.connections
            ]
            self._save_and_refresh(connections)
            log.info("Edited connection '%s'.", updated["name"])

    def _on_delete(self) -> None:
        """Confirm and delete the selected connection."""
        conn = self._selected_connection()
        if not conn:
            return
        name   = conn.get("name", "this connection")
        result = QMessageBox.question(
            self._central,
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

    def _on_connect(self) -> None:
        """Launch the selected connection."""
        conn = self._selected_connection()
        if not conn:
            return
        name = conn.get("name", "unknown")
        log.info("Connect requested for '%s'.", name)
        try:
            self._launcher.launch(conn)
        except NmkitError as exc:
            log.error("Launch failed for '%s': %s", name, exc)
            QMessageBox.critical(self._central, "Launch Failed", str(exc))

    def _on_view_details(self) -> None:
        """Open View Details dialog (read-only)."""
        conn = self._selected_connection()
        if not conn:
            return
        dialog = ConnectionDialog(
            connection=conn,
            read_only=True,
            parent=self._central,
        )
        dialog.exec()

    def _save_and_refresh(self, connections: list) -> None:
        """Save connections to disk and refresh the list."""
        try:
            self._config.save_connections(connections)
        except NmkitConfigError as exc:
            log.error("Failed to save connections: %s", exc)
            QMessageBox.critical(self._central, "Save Failed", str(exc))
            return
        self._setup_list()
        self._update_buttons(False)

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

        show_action.triggered.connect(self._on_tray_show)              # pylint: disable=no-member
        quit_action.triggered.connect(self._on_tray_quit)              # pylint: disable=no-member
        force_quit_action.triggered.connect(self._on_tray_force_quit)  # pylint: disable=no-member

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)          # pylint: disable=no-member
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

    def _on_tray_quit(self) -> None:
        """Graceful quit."""
        log.info("Quit requested from tray.")
        self._tray.hide()
        self._app.quit()

    def _on_tray_force_quit(self) -> None:
        """Hard kill."""
        log.warning("Force Quit requested from tray.")
        os._exit(0)  # pylint: disable=protected-access

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        """Double-click tray icon shows the window."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_tray_show()
