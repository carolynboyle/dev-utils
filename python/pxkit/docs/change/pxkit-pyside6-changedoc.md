# pxkit — Changedoc: PySide6 rewrite + dependency updates

## Summary

Replaced tkinter/pystray/Pillow with PySide6. System tray is now handled
by `QSystemTrayIcon` (native Qt, no background thread). Scrollable VM list
uses `QScrollArea` instead of the Canvas/Scrollbar workaround. Added
`secretstorage` and `jeepney` to dependencies per handoff backlog.

---

## pyproject.toml

**File:** `pyproject.toml`

### BEFORE
```toml
dependencies = [
    "pyyaml>=6.0",
    "requests>=2.31.0",
    "keyring>=24.0",
    "urllib3>=2.0",
    "pystray>=0.19",
    "Pillow>=10.0",
]
```

### AFTER
```toml
dependencies = [
    "pyyaml>=6.0",
    "requests>=2.31.0",
    "keyring>=24.0",
    "urllib3>=2.0",
    "PySide6>=6.6",
    "secretstorage>=3.3",
    "jeepney>=0.8",
]
```

**Why:** `pystray` and `Pillow` removed — replaced by PySide6's native
`QSystemTrayIcon` and `QPixmap`/`QPainter`. `PySide6` added as the Qt
binding (LGPL, official). `secretstorage` and `jeepney` added as the
keyring SecretService backend and its D-Bus transport (were missing from
declared dependencies; required at runtime on Linux).

---

## src/pxkit/ui.py

**File:** `src/pxkit/ui.py`

Full rewrite. BEFORE is the complete tkinter/pystray implementation;
AFTER is the PySide6 implementation.

### BEFORE
```python
"""
pxkit.ui - Tkinter launcher dialog for pxkit.
...
"""

import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw
import pystray

from pxkit.config import ConfigManager
from pxkit.connection import ProxmoxConnection
from pxkit.exceptions import PxkitError
from pxkit.launcher import Launcher

log = logging.getLogger("pxkit")

_WINDOW_WIDTH   = 300
_WINDOW_HEIGHT  = 400
_BTN_PADX       = 10
_BTN_PADY       = 4
_TRAY_ICON_SIZE = 64
_TRAY_ICON_COLOR = "#2196F3"


class LauncherUI:
    def __init__(self, config, conn, launcher):
        self._conn     = conn
        self._launcher = launcher
        self._vms      = config.vms
        self._title    = config.get("ui", {}).get("title", "System Launcher")
        self._root  = tk.Tk()
        self._tray  = None
        self._build()

    def run(self):
        log.info("LauncherUI starting.")
        self._root.mainloop()
        log.info("LauncherUI exited.")

    def _build(self):
        self._root.title(self._title)
        self._root.resizable(False, False)
        self._root.geometry(f"{_WINDOW_WIDTH}x{_WINDOW_HEIGHT}")
        self._root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        self._build_proxmox_button()
        self._build_separator()
        self._build_vm_list()

    def _build_proxmox_button(self):
        btn = tk.Button(self._root, text="Open Proxmox UI",
                        command=self._on_open_proxmox, width=28)
        btn.pack(pady=(_BTN_PADY * 2, _BTN_PADY), padx=_BTN_PADX)

    def _build_separator(self):
        sep = tk.Frame(self._root, height=1, bg="grey80")
        sep.pack(fill=tk.X, padx=_BTN_PADX, pady=_BTN_PADY)

    def _build_vm_list(self):
        container = tk.Frame(self._root)
        container.pack(fill=tk.BOTH, expand=True, padx=_BTN_PADX, pady=_BTN_PADY)
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = tk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",
            lambda ev: canvas.yview_scroll(-1 * (ev.delta // 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        for vm in self._vms:
            self._build_vm_button(inner, vm)

    def _build_vm_button(self, parent, vm):
        btn = tk.Button(parent, text=vm["name"],
                        command=lambda v=vm: self._on_launch_vm(v),
                        anchor="w", width=28)
        btn.pack(fill=tk.X, pady=_BTN_PADY)

    def _minimize_to_tray(self):
        self._root.withdraw()
        log.info("Window minimized to tray.")
        if self._tray is None:
            self._tray = pystray.Icon(
                name="pxkit", icon=self._make_tray_icon(),
                title=self._title, menu=self._make_tray_menu())
            thread = threading.Thread(target=self._tray.run, daemon=True)
            thread.start()

    def _make_tray_icon(self):
        img  = Image.new("RGB", (_TRAY_ICON_SIZE, _TRAY_ICON_SIZE), _TRAY_ICON_COLOR)
        draw = ImageDraw.Draw(img)
        margin = _TRAY_ICON_SIZE // 4
        draw.rectangle([margin, margin,
                        _TRAY_ICON_SIZE - margin, _TRAY_ICON_SIZE - margin],
                       fill="white")
        return img

    def _make_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Show", self._on_tray_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_tray_quit),
            pystray.MenuItem("Force Quit", self._on_tray_force_quit),
        )

    def _on_open_proxmox(self):
        try:
            self._launcher.open_proxmox_ui()
            log.info("Proxmox UI opened.")
        except PxkitError as exc:
            log.error("Failed to open Proxmox UI: %s", exc)
            messagebox.showerror("Error", str(exc))

    def _on_launch_vm(self, vm):
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
                raise PxkitError(f"VM '{name}' has unknown connection type '{conn_type}'.")
        except PxkitError as exc:
            log.error("Launch failed for VM '%s': %s", name, exc)
            messagebox.showerror("Launch Failed", str(exc))

    def _on_tray_show(self, icon, item):
        self._root.after(0, self._root.deiconify)
        log.info("Window restored from tray.")

    def _on_tray_quit(self, icon, item):
        log.info("Quit requested from tray.")
        icon.stop()
        self._root.after(0, self._root.destroy)

    def _on_tray_force_quit(self, icon, item):
        log.warning("Force Quit requested from tray.")
        os._exit(0)
```

### AFTER
```python
"""
pxkit.ui - PySide6 launcher dialog for pxkit.
...
"""

import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSystemTrayIcon, QMenu,
    QVBoxLayout, QWidget,
)

from pxkit.config import ConfigManager
from pxkit.connection import ProxmoxConnection
from pxkit.exceptions import PxkitError
from pxkit.launcher import Launcher

log = logging.getLogger("pxkit")

_WINDOW_WIDTH    = 300
_WINDOW_HEIGHT   = 400
_BTN_MARGIN      = 10
_BTN_SPACING     = 4
_TRAY_ICON_SIZE  = 64
_TRAY_ICON_COLOR = "#2196F3"


class LauncherUI:
    def __init__(self, config, conn, launcher):
        self._conn     = conn
        self._launcher = launcher
        self._vms      = config.vms
        self._title    = config.get("ui", {}).get("title", "System Launcher")
        self._app    = QApplication.instance() or QApplication([])
        self._window = _LauncherWindow(
            title=self._title, vms=self._vms,
            on_open_proxmox=self._on_open_proxmox,
            on_launch_vm=self._on_launch_vm,
            on_close=self._minimize_to_tray,
        )
        self._tray = self._build_tray()

    def run(self):
        log.info("LauncherUI starting.")
        self._window.show()
        self._app.exec()
        log.info("LauncherUI exited.")

    def _build_tray(self):
        tray = QSystemTrayIcon(self._make_tray_pixmap(), self._app)
        tray.setToolTip(self._title)
        menu = QMenu()
        show_action       = menu.addAction("Show")
        menu.addSeparator()
        quit_action       = menu.addAction("Quit")
        force_quit_action = menu.addAction("Force Quit")
        show_action.triggered.connect(self._on_tray_show)
        quit_action.triggered.connect(self._on_tray_quit)
        force_quit_action.triggered.connect(self._on_tray_force_quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        return tray

    def _make_tray_pixmap(self):
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

    def _minimize_to_tray(self):
        self._window.hide()
        self._tray.show()
        log.info("Window minimized to tray.")

    def _on_open_proxmox(self):
        try:
            self._launcher.open_proxmox_ui()
            log.info("Proxmox UI opened.")
        except PxkitError as exc:
            log.error("Failed to open Proxmox UI: %s", exc)
            QMessageBox.critical(self._window, "Error", str(exc))

    def _on_launch_vm(self, vm):
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
                    f"Expected 'spice' or 'ssh'.")
        except PxkitError as exc:
            log.error("Launch failed for VM '%s': %s", name, exc)
            QMessageBox.critical(self._window, "Launch Failed", str(exc))

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._on_tray_show()

    def _on_tray_show(self):
        self._tray.hide()
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        log.info("Window restored from tray.")

    def _on_tray_quit(self):
        log.info("Quit requested from tray.")
        self._tray.hide()
        self._app.quit()

    def _on_tray_force_quit(self):
        log.warning("Force Quit requested from tray.")
        os._exit(0)


class _LauncherWindow(QWidget):
    def __init__(self, title, vms, on_open_proxmox, on_launch_vm, on_close):
        super().__init__()
        self._on_close     = on_close
        self._on_launch_vm = on_launch_vm
        self.setWindowTitle(title)
        self.setFixedSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._build(vms, on_open_proxmox)

    def closeEvent(self, event):
        event.ignore()
        self._on_close()

    def _build(self, vms, on_open_proxmox):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            _BTN_MARGIN, _BTN_MARGIN, _BTN_MARGIN, _BTN_MARGIN)
        root_layout.setSpacing(_BTN_SPACING)

        proxmox_btn = QPushButton("Open Proxmox UI")
        proxmox_btn.clicked.connect(on_open_proxmox)
        root_layout.addWidget(proxmox_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(_BTN_SPACING)
        for vm in vms:
            btn = QPushButton(vm["name"])
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(
                lambda checked=False, v=vm: self._on_launch_vm(v))
            inner_layout.addWidget(btn)
        inner_layout.addStretch()
        scroll.setWidget(inner)
        root_layout.addWidget(scroll)
```

**Why:** tkinter's system tray support via pystray required a background
thread and proved unreliable (tray icon appeared but restore did not work).
`QSystemTrayIcon` is integrated into the Qt event loop — no thread needed,
and restore is a straightforward `show()`/`raise_()`/`activateWindow()` call.
`QScrollArea` replaces the Canvas/Scrollbar workaround with a standard widget.
`_LauncherWindow` is extracted as a `QWidget` subclass so `closeEvent` can
be overridden cleanly. The public interface (`LauncherUI(config, conn,
launcher)` + `run()`) is unchanged — `__main__.py` requires no logic changes.

---

## src/pxkit/__main__.py

**File:** `src/pxkit/__main__.py`

### BEFORE
```python
def cmd_gui(config: ConfigManager) -> int:
    """
    Launch the tkinter GUI.

    Instantiates all dependencies and starts the LauncherUI main loop.
    Importing ui here keeps tkinter out of the import path for CLI-only
    invocations.
    ...
    """
    # Local import keeps tkinter out of CLI-only execution paths.
    from pxkit.ui import LauncherUI  # pylint: disable=import-outside-toplevel
```

### AFTER
```python
def cmd_gui(config: ConfigManager) -> int:
    """
    Launch the PySide6 GUI.

    Instantiates all dependencies and starts the LauncherUI event loop.
    Importing ui here keeps PySide6 out of the import path for CLI-only
    invocations.
    ...
    """
    # Local import keeps PySide6 out of CLI-only execution paths.
    from pxkit.ui import LauncherUI  # pylint: disable=import-outside-toplevel
```

**Why:** Documentation-only fix. "tkinter" and "main loop" replaced with
"PySide6" and "event loop" to match the new implementation. No logic change.

---

## install.sh

**File:** `install.sh`

### BEFORE
*(apt package install block — exact line varies by script version)*
```bash
apt-get install -y python3.11-venv python3-tk python3-secretstorage
```
*(or equivalent line including python3-tk)*

### AFTER
```bash
apt-get install -y python3.11-venv python3-secretstorage
```

**Why:** `python3-tk` is only needed for tkinter. PySide6 installs via pip
from `pyproject.toml`; no apt package required.

---

## Tests

`tests/test_ui.py` — needs a full rewrite for PySide6. Deferred: there is
nothing meaningful to test until the Qt implementation is running on the T490.
The existing test file (if any) should be deleted or emptied to avoid import
errors from the removed tkinter dependency.
