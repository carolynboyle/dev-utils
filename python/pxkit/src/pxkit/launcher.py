"""
pxkit.launcher - Proxmox web UI and SPICE console launcher.

Opens the Proxmox web UI in the system default browser, launches
remote-viewer for SPICE console access, and opens SSH terminal
sessions in the configured terminal emulator.

SPICE launch flow:
  1. Receive .vv content string from ProxmoxConnection
  2. Write to a named temp file
  3. Launch remote-viewer on the temp file
  4. Wait for remote-viewer to read the file, then clean up

SSH launch flow (future):
  1. Build ssh command from VM connection config
  2. Launch configured terminal emulator with exec_flag and ssh command

Usage:
    from pxkit.config import ConfigManager
    from pxkit.launcher import Launcher

    config = ConfigManager()
    launcher = Launcher(config)

    launcher.open_proxmox_ui()
    launcher.launch_spice(vv_content)
    launcher.launch_ssh(vm)
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
    Opens the Proxmox web UI, launches SPICE console sessions, and
    opens SSH terminal sessions.

    Uses the system default browser for the web UI, remote-viewer for
    SPICE consoles, and the configured terminal emulator for SSH.
    No browser or terminal is hardcoded — all are driven by config.

    Usage:
        launcher = Launcher(config)
        launcher.open_proxmox_ui()
        launcher.launch_spice(vv_content)
        launcher.launch_ssh(vm)
    """

    def __init__(self, config: ConfigManager):
        """
        Initialise Launcher.

        Args:
            config: Loaded ConfigManager instance.
        """
        self._proxmox  = config.proxmox
        self._terminal = config.get("terminal", {})

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

        try:
            subprocess.Popen(  # pylint: disable=consider-using-with
                ["remote-viewer", str(vv_path)],
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

    def launch_ssh(self, vm: dict) -> None:
        """
        Launch an SSH terminal session for a VM.

        Opens the configured terminal emulator with an SSH command
        built from the VM's connection config (host, user, key).

        Args:
            vm: VM dict from config.vms, with connection keys:
                type (must be 'ssh'), host, user, key.

        Raises:
            PxkitLaunchError: If the terminal emulator cannot be
                              launched or terminal config is missing.
        """
        # SSH launch not yet implemented.
        # Stub is here to confirm the interface and config shape.
        # Implementation will follow once SPICE path is validated.
        name = vm.get("name", vm.get("vmid", "unknown"))
        log.warning("launch_ssh called for '%s' but SSH launch is not yet implemented.", name)
        raise PxkitLaunchError(
            f"SSH launch for '{name}' is not yet implemented."
        )

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
                return Path(tmp.name)
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
