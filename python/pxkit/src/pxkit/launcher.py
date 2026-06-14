"""
pxkit.launcher - Proxmox web UI and SPICE console launcher.

Opens the Proxmox web UI in the system default browser, and launches
remote-viewer for SPICE console access.

SPICE launch flow:
  1. Receive .vv content string from ProxmoxConnection
  2. Pipe directly to remote-viewer via stdin — no temp file, no expiry window

Usage:
    from pxkit.config import ConfigManager
    from pxkit.launcher import Launcher

    config = ConfigManager()
    launcher = Launcher(config)

    launcher.open_proxmox_ui()
    launcher.launch_spice(vv_content)
"""

import logging
import subprocess
import webbrowser
from pathlib import Path

from pxkit.config import ConfigManager
from pxkit.exceptions import PxkitLaunchError

log = logging.getLogger("pxkit")


# ---------------------------------------------------------------------------
# Launcher
# ---------------------------------------------------------------------------

class Launcher:
    """
    Opens the Proxmox web UI and launches SPICE console sessions.

    Uses the system default browser for the web UI and remote-viewer
    for SPICE consoles. No browser is hardcoded — system default is
    used for maximum portability across machines.

    Usage:
        launcher = Launcher(config)
        launcher.open_proxmox_ui()
        launcher.launch_spice(vv_content)
    """

    def __init__(self, config: ConfigManager):
        """
        Initialise Launcher.

        Args:
            config: Loaded ConfigManager instance.
        """
        self._proxmox = config.proxmox

    # -- Public interface -----------------------------------------------------

    def open_proxmox_ui(self) -> None:
        """
        Open the Proxmox web UI in the system default browser.

        Builds the URL from the proxmox config (host and port) and
        opens it with webbrowser.open(). No browser is hardcoded.

        Raises:
            PxkitLaunchError: If the browser cannot be opened.
        """
        url = self._build_ui_url()
        log.debug("Opening Proxmox UI: %s", url)

        try:
            webbrowser.open(url)
        except Exception as exc:
            raise PxkitLaunchError(
                f"Failed to open Proxmox web UI at {url}: {exc}"
            ) from exc

    def launch_spice(self, vv_content: str) -> None:
        """
        Launch a SPICE console session via remote-viewer.

        Pipes .vv content directly to remote-viewer via stdin, avoiding
        any temp file latency that could cause ticket expiry before
        remote-viewer connects.

        A debug copy is saved to ~/.local/share/pxkit/last-spice.vv
        for inspection — this copy is not used by remote-viewer.

        Args:
            vv_content: SPICE .vv file content as a string, as returned
                        by ProxmoxConnection.get_spice_ticket().

        Raises:
            PxkitLaunchError: If remote-viewer cannot be launched.
        """
        # Save debug copy only when DEBUG logging is active
        if log.isEnabledFor(logging.DEBUG):
            debug_copy = Path.home() / ".local" / "share" / "pxkit" / "last-spice.vv"
            debug_copy.write_text(vv_content, encoding="utf-8")
            log.debug("Debug .vv copy saved to %s", debug_copy)

        log.debug("Launching remote-viewer via stdin pipe.")

        try:
            process = subprocess.Popen(
                ["remote-viewer", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Write ticket and close stdin immediately — remote-viewer
            # reads it on startup; we do not wait for it to exit so
            # the pxkit window stays responsive.
            process.stdin.write(vv_content.encode("utf-8"))
            process.stdin.close()
        except FileNotFoundError as exc:
            raise PxkitLaunchError(
                "remote-viewer not found. Install it with: "
                "apt install virt-viewer"
            ) from exc
        except OSError as exc:
            raise PxkitLaunchError(
                f"Failed to launch remote-viewer: {exc}"
            ) from exc

    # -- Internal -------------------------------------------------------------

    def launch_ssh(self, vm: dict) -> None:
        """
        Launch an SSH terminal session for a VM.

        Not yet implemented.

        Args:
            vm: VM dict from config.vms.

        Raises:
            PxkitLaunchError: Always — SSH launch is not yet implemented.
        """
        name = vm.get("name", str(vm.get("vmid", "unknown")))
        raise PxkitLaunchError(
            f"SSH launch for VM '{name}' is not yet implemented."
        )

    def _build_ui_url(self) -> str:
        """
        Build the Proxmox web UI URL from config.

        Returns:
            Full HTTPS URL string for the Proxmox web interface.
        """
        host = self._proxmox["host"]
        port = self._proxmox["port"]
        return f"https://{host}:{port}"


