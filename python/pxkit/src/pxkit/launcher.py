"""
pxkit.launcher - Proxmox web UI and SPICE console launcher.

Opens the Proxmox web UI in the system default browser, and launches
remote-viewer for SPICE console access.

SPICE launch flow:
  1. Receive .vv content string from ProxmoxConnection
  2. Write to a named temp file
  3. Launch remote-viewer on the temp file
  4. Wait for remote-viewer to read the file, then clean up

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
import tempfile
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

        Writes the .vv content to a named temp file, launches
        remote-viewer on it, waits for remote-viewer to read the file,
        then cleans up the temp file.

        Args:
            vv_content: SPICE .vv file content as a string, as returned
                        by ProxmoxConnection.get_spice_ticket().

        Raises:
            PxkitLaunchError: If remote-viewer cannot be launched or
                              the temp file cannot be written.
        """
        vv_path = self._write_temp_vv(vv_content)
        log.debug("SPICE temp file written: %s", vv_path)

        # Save a debug copy that persists after remote-viewer deletes the original
        debug_copy = Path.home() / ".local" / "share" / "pxkit" / "last-spice.vv"
        debug_copy.write_text(vv_content, encoding="utf-8")
        log.debug("Debug .vv copy saved to %s", debug_copy)

        cmd = ["remote-viewer", str(vv_path)]
        log.debug("Launching remote-viewer: %s", " ".join(cmd))

        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise PxkitLaunchError(
                "remote-viewer not found. Install it with: "
                "apt install virt-viewer"
            ) from exc
        except OSError as exc:
            raise PxkitLaunchError(
                f"Failed to launch remote-viewer: {exc}"
            ) from exc
        finally:
            self._cleanup_temp(vv_path)

    # -- Internal -------------------------------------------------------------

    def _build_ui_url(self) -> str:
        """
        Build the Proxmox web UI URL from config.

        Returns:
            Full HTTPS URL string for the Proxmox web interface.
        """
        host = self._proxmox["host"]
        port = self._proxmox["port"]
        return f"https://{host}:{port}"

    @staticmethod
    def _write_temp_vv(vv_content: str) -> Path:
        """
        Write .vv content to a named temporary file.

        Uses delete=False so the file persists after close, allowing
        remote-viewer to open it by path.

        Args:
            vv_content: SPICE .vv file content as a string.

        Returns:
            Path to the written temp file.

        Raises:
            PxkitLaunchError: If the file cannot be written.
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".vv",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(vv_content)
                path = Path(tmp.name)
                log.debug("Wrote SPICE temp file: %s", path)
                return path
        except OSError as exc:
            raise PxkitLaunchError(
                f"Failed to write SPICE temp file: {exc}"
            ) from exc

    @staticmethod
    def _cleanup_temp(path: Path) -> None:
        """
        Delete a temporary file, ignoring errors if already gone.

        Args:
            path: Path to the temp file to delete.
        """
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
