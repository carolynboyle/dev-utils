"""
pxkit.ui - PySide6 launcher dialog for pxkit.

Displays a scrollable list of VM launch buttons and a button to open
the Proxmox web UI. Owns no logic — all actions delegate to Launcher
and ProxmoxConnection. Errors are surfaced via QMessageBox.

Minimizing closes the window to the system tray via QSystemTrayIcon.
The tray icon provides Show, Quit, and Force Quit options.

Usage:
    from pxkit.config import ConfigManager
    from pxkit.connection import ProxmoxConnection
    from pxkit.launcher import Launcher
    from pxkit.ui import LauncherUI

    config = ConfigManager()
    conn   = ProxmoxConnection(config)
    launcher = Launcher(config)

    app = LauncherUI(config, conn, launcher)
    app.run()
"""

import logging
import os

from PySide6.QtCore import Qt  # pylint: disable=import-error
from PySide6.QtGui import QColor, QPainter, QPixmap  # pylint: disable=import-error
from PySide6.QtWidgets import (  # pylint: disable=import-error
    QApplication,
    QFrame,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSystemTrayIcon,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from pxkit.config import ConfigManager
from pxkit.connection import ProxmoxConnection
from pxkit.exceptions import PxkitError
from pxkit.launcher import Launcher

log = logging.getLogger("pxkit")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WINDOW_WIDTH    = 300
_WINDOW_HEIGHT   = 400
_BTN_MARGIN      = 10
_BTN_SPACING     = 4
_TRAY_ICON_SIZE  = 64
_TRAY_ICON_COLOR = "#2196F3"  # Material Blue 500


# ---------------------------------------------------------------------------
# LauncherUI
# ---------------------------------------------------------------------------

class LauncherUI:  # pylint: disable=too-few-public-methods
    """
    PySide6 launcher dialog.

    Builds a fixed-size window with a Proxmox UI button at the top and
    a scrollable list of VM buttons below. Closing the window sends it
    to the system tray via QSystemTrayIcon.

    Owns no business logic — all actions delegate to the Launcher and
    ProxmoxConnection instances passed at construction.

    Usage:
        app = LauncherUI(config, conn, launcher)
        app.run()
    """

    def __init__(
        self,
        config: ConfigManager,
        conn: ProxmoxConnection,
        launcher: Launcher,
    ):
        """
        Initialise LauncherUI.

        Args:
            config:   Loaded ConfigManager instance.
            conn:     ProxmoxConnection instance for SPICE ticket retrieval.
            launcher: Launcher instance for opening UI and consoles.
        """
        self._conn     = conn
        self._launcher = launcher
        self._vms      = config.vms
        self._title    = config.get("ui", {}).get("title", "System Launcher")

        self._app    = QApplication.instance() or QApplication([])
        self._window = _LauncherWindow(
            self._title,
            self._vms,
            on_open_proxmox = self._on_open_proxmox,
            on_launch_vm    = self._on_launch_vm,
            on_close        = self._minimize_to_tray,
        )
        self._tray = self._build_tray()

    # -- Public interface -----------------------------------------------------

    def run(self) -> None:
        """
        Start the Qt event loop.

        Blocks until the application quits (via tray Quit or Force Quit).
        """
        log.info("LauncherUI starting.")
        self._window.show()
        self._app.exec()
        log.info("LauncherUI exited.")

    # -- Tray -----------------------------------------------------------------

    def _build_tray(self) -> QSystemTrayIcon:
        """
        Build and return the system tray icon.

        The tray icon is hidden until the window is minimized.
        Left-click restores the window; right-click opens the menu.

        Returns:
            Configured QSystemTrayIcon (not yet visible).
        """
        tray = QSystemTrayIcon(self._make_tray_pixmap(), self._app)
        tray.setToolTip(self._title)

        menu = QMenu()
        show_action        = menu.addAction("Show")
        menu.addSeparator()
        quit_action        = menu.addAction("Quit")
        force_quit_action  = menu.addAction("Force Quit")

        show_action.triggered.connect(self._on_tray_show)
        quit_action.triggered.connect(self._on_tray_quit)
        force_quit_action.triggered.connect(self._on_tray_force_quit)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)

        return tray

    def _make_tray_pixmap(self) -> QPixmap:
        """
        Generate a simple tray icon programmatically.

        Returns:
            QPixmap — solid blue square with a white inset rectangle.
        """
        size   = _TRAY_ICON_SIZE
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(_TRAY_ICON_COLOR))

        painter = QPainter(pixmap)
        painter.setBrush(QColor("white"))
        painter.setPen(Qt.PenStyle.NoPen)
        margin = size // 4
        painter.drawRect(margin, margin, size - margin * 2, size - margin * 2)
        painter.end()

        return pixmap

    def _minimize_to_tray(self) -> None:
        """
        Hide the window and show the tray icon.

        Called when the user clicks the window close button.
        """
        self._window.hide()
        self._tray.show()
        log.info("Window minimized to tray.")

    # -- Event handlers -------------------------------------------------------

    def _on_open_proxmox(self) -> None:
        """Handle Open Proxmox UI button click."""
        try:
            self._launcher.open_proxmox_ui()
            log.info("Proxmox UI opened.")
        except PxkitError as exc:
            log.error("Failed to open Proxmox UI: %s", exc)
            QMessageBox.critical(self._window, "Error", str(exc))

    def _on_launch_vm(self, vm: dict) -> None:
        """
        Handle a VM button click.

        Dispatches to the correct launch method based on
        connection.type. Errors are shown in a QMessageBox.

        Args:
            vm: VM dict from config.vms.
        """
        conn_type = vm.get("connection", {}).get("type")
        name      = vm.get("name", str(vm.get("vmid", "unknown")))

        log.info("Launch requested for VM '%s' (type: %s).", name, conn_type)

        try:
            if conn_type == "spice":
                vv_content = self._conn.get_spice_ticket(vm)
                self._launcher.launch_spice(vv_content)
            elif conn_type == "ssh":
                self._launcher.launch_ssh(vm)
            else:
                raise PxkitError(
                    f"VM '{name}' has unknown connection type '{conn_type}'. "
                    f"Expected 'spice' or 'ssh'."
                )
        except PxkitError as exc:
            log.error("Launch failed for VM '%s': %s", name, exc)
            QMessageBox.critical(self._window, "Launch Failed", str(exc))

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Restore window on tray icon left-click or double-click."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._on_tray_show()

    def _on_tray_show(self) -> None:
        """Restore window from tray."""
        self._tray.hide()
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        log.info("Window restored from tray.")

    def _on_tray_quit(self) -> None:
        """Graceful quit from tray menu."""
        log.info("Quit requested from tray.")
        self._tray.hide()
        self._app.quit()

    def _on_tray_force_quit(self) -> None:
        """
        Hard kill from tray menu.

        Uses os._exit(0) to bypass any frozen event loop.
        Labeled Force Quit in the menu so the intent is clear.
        """
        log.warning("Force Quit requested from tray.")
        os._exit(0)  # pylint: disable=protected-access


# ---------------------------------------------------------------------------
# _LauncherWindow  (internal)
# ---------------------------------------------------------------------------

class _LauncherWindow(QWidget):  # pylint: disable=too-few-public-methods
    """
    The main window widget.

    Separated from LauncherUI so the close event can be intercepted
    cleanly without subclassing QApplication.
    """

    def __init__(
        self,
        title: str,
        vms: list,
        *,
        on_open_proxmox,
        on_launch_vm,
        on_close,
    ):
        super().__init__()
        self._on_close       = on_close
        self._on_launch_vm   = on_launch_vm

        self.setWindowTitle(title)
        self.setFixedSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)

        self._build(vms, on_open_proxmox)

    def closeEvent(self, event):  # pylint: disable=invalid-name
        """Intercept window close — minimize to tray instead of quitting."""
        event.ignore()
        self._on_close()

    # -- Build ----------------------------------------------------------------

    def _build(self, vms: list, on_open_proxmox) -> None:
        """Construct the window layout."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(_BTN_MARGIN, _BTN_MARGIN, _BTN_MARGIN, _BTN_MARGIN)
        root_layout.setSpacing(_BTN_SPACING)

        # Proxmox UI button
        proxmox_btn = QPushButton("Open Proxmox UI")
        proxmox_btn.clicked.connect(on_open_proxmox)
        root_layout.addWidget(proxmox_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(sep)

        # Scrollable VM list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(_BTN_SPACING)

        for vm in vms:
            btn = QPushButton(vm["name"])
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked=False, v=vm: self._on_launch_vm(v))
            inner_layout.addWidget(btn)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        root_layout.addWidget(scroll)
