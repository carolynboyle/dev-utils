"""
pxkit.ui - Tkinter launcher dialog for pxkit.

Displays a scrollable list of VM launch buttons and a button to open
the Proxmox web UI. Owns no logic — all actions delegate to Launcher
and ProxmoxConnection. Errors are surfaced via messagebox.

Minimizing closes the window to the system tray (via pystray).
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WINDOW_WIDTH   = 300
_WINDOW_HEIGHT  = 400
_BTN_PADX       = 10
_BTN_PADY       = 4
_TRAY_ICON_SIZE = 64
_TRAY_ICON_COLOR = "#2196F3"  # Material Blue 500


# ---------------------------------------------------------------------------
# LauncherUI
# ---------------------------------------------------------------------------

class LauncherUI:  # pylint: disable=too-few-public-methods
    """
    Tkinter launcher dialog.

    Builds a fixed-size window with a Proxmox UI button at the top and
    a scrollable list of VM buttons below. Minimizing sends the window
    to the system tray.

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

        self._root  = tk.Tk()
        self._tray  = None
        self._build()

    # -- Public interface -----------------------------------------------------

    def run(self) -> None:
        """
        Start the tkinter main loop.

        Blocks until the window is closed or Force Quit is selected
        from the tray menu.
        """
        log.info("LauncherUI starting.")
        self._root.mainloop()
        log.info("LauncherUI exited.")

    # -- Build ----------------------------------------------------------------

    def _build(self) -> None:
        """
        Construct the window layout.

        Sets window title, size, and close behaviour, then builds the
        Proxmox UI button and scrollable VM list.
        """
        self._root.title(self._title)
        self._root.resizable(False, False)
        self._root.geometry(f"{_WINDOW_WIDTH}x{_WINDOW_HEIGHT}")
        self._root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        self._build_proxmox_button()
        self._build_separator()
        self._build_vm_list()

    def _build_proxmox_button(self) -> None:
        """Add the Open Proxmox UI button at the top of the window."""
        btn = tk.Button(
            self._root,
            text="Open Proxmox UI",
            command=self._on_open_proxmox,
            width=28,
        )
        btn.pack(pady=(_BTN_PADY * 2, _BTN_PADY), padx=_BTN_PADX)

    def _build_separator(self) -> None:
        """Add a visual separator between the Proxmox button and VM list."""
        sep = tk.Frame(self._root, height=1, bg="grey80")
        sep.pack(fill=tk.X, padx=_BTN_PADX, pady=_BTN_PADY)

    def _build_vm_list(self) -> None:
        """
        Build the scrollable VM button list.

        Uses a Canvas + Scrollbar + inner Frame pattern so the list
        can grow beyond the window height without clipping.
        """
        container = tk.Frame(self._root)
        container.pack(fill=tk.BOTH, expand=True, padx=_BTN_PADX, pady=_BTN_PADY)

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        # Resize canvas scroll region when inner frame changes size.
        def _on_inner_configure(event):  # pylint: disable=unused-argument
            canvas.configure(scrollregion=canvas.bbox("all"))

        # Keep inner frame width in sync with canvas width.
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel scrolling — bind on enter, unbind on leave so the
        # scroll wheel doesn't get captured when the cursor is elsewhere.
        def _on_mousewheel(ev):
            canvas.yview_scroll(-1 * (ev.delta // 120), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for vm in self._vms:
            self._build_vm_button(inner, vm)

    def _build_vm_button(self, parent: tk.Frame, vm: dict) -> None:
        """
        Add a single VM launch button to the scrollable list.

        Args:
            parent: The inner frame inside the scrollable canvas.
            vm:     VM dict from config.vms.
        """
        btn = tk.Button(
            parent,
            text=vm["name"],
            command=lambda v=vm: self._on_launch_vm(v),
            anchor="w",
            width=28,
        )
        btn.pack(fill=tk.X, pady=_BTN_PADY)

    # -- Tray -----------------------------------------------------------------

    def _minimize_to_tray(self) -> None:
        """
        Hide the window and start the system tray icon.

        Called when the user clicks the window close button.
        The tray icon runs in a background thread so it does not
        block the tkinter main loop.
        """
        self._root.withdraw()
        log.info("Window minimized to tray.")

        if self._tray is None:
            self._tray = pystray.Icon(
                name="pxkit",
                icon=self._make_tray_icon(),
                title=self._title,
                menu=self._make_tray_menu(),
            )
            thread = threading.Thread(target=self._tray.run, daemon=True)
            thread.start()

    def _make_tray_icon(self) -> Image.Image:
        """
        Generate a simple tray icon programmatically.

        Returns:
            A PIL Image — solid blue square with rounded feel.
        """
        img  = Image.new("RGB", (_TRAY_ICON_SIZE, _TRAY_ICON_SIZE), _TRAY_ICON_COLOR)
        draw = ImageDraw.Draw(img)
        # Small white square inset as a minimal visual marker.
        margin = _TRAY_ICON_SIZE // 4
        draw.rectangle(
            [margin, margin, _TRAY_ICON_SIZE - margin, _TRAY_ICON_SIZE - margin],
            fill="white",
        )
        return img

    def _make_tray_menu(self) -> pystray.Menu:
        """
        Build the right-click tray menu.

        Returns:
            pystray.Menu with Show, Quit, and Force Quit items.
        """
        return pystray.Menu(
            pystray.MenuItem("Show", self._on_tray_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_tray_quit),
            pystray.MenuItem("Force Quit", self._on_tray_force_quit),
        )

    # -- Event handlers -------------------------------------------------------

    def _on_open_proxmox(self) -> None:
        """Handle Open Proxmox UI button click."""
        try:
            self._launcher.open_proxmox_ui()
            log.info("Proxmox UI opened.")
        except PxkitError as exc:
            log.error("Failed to open Proxmox UI: %s", exc)
            messagebox.showerror("Error", str(exc))

    def _on_launch_vm(self, vm: dict) -> None:
        """
        Handle a VM button click.

        Dispatches to the correct launch method based on
        connection.type. Errors are shown in a messagebox.

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
            messagebox.showerror("Launch Failed", str(exc))

    def _on_tray_show(self, icon, item):  # pylint: disable=unused-argument
        """Restore window from tray."""
        self._root.after(0, self._root.deiconify)
        log.info("Window restored from tray.")

    def _on_tray_quit(self, icon, item):  # pylint: disable=unused-argument
        """Graceful quit from tray menu."""
        log.info("Quit requested from tray.")
        icon.stop()
        self._root.after(0, self._root.destroy)

    def _on_tray_force_quit(self, icon, item):  # pylint: disable=unused-argument
        """
        Hard kill from tray menu.

        Uses os._exit(0) to bypass any frozen event loop.
        Labeled Force Quit in the menu so the intent is clear.
        """
        log.warning("Force Quit requested from tray.")
        os._exit(0)  # pylint: disable=protected-access
