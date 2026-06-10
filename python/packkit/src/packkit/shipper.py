"""
shipper.py — Optional remote transfer for pack-kit.

Transfers the completed tarball to a remote host via scp.
Only runs when ship.enabled is true in the config.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from packkit.config import ShipConfig
from packkit.exceptions import ScpError


class Shipper:
    """
    Transfers a tarball to a remote host via scp.

    Args:
        ship_config: Validated ShipConfig.
    """

    def __init__(self, ship_config: ShipConfig) -> None:
        self._config = ship_config

    def ship(self, tarball: Path) -> None:
        """
        Transfer the tarball to the configured remote host.

        Args:
            tarball: Path to the local tarball to transfer.

        Raises:
            ScpError: If the transfer fails or scp cannot be executed.
        """
        destination = f"{self._config.user}@{self._config.host}:{self._config.path}"

        cmd = ['scp', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no']
        if self._config.key:
            cmd += ['-i', self._config.key]
        cmd += [str(tarball), destination]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise ScpError(
                f"scp transfer timed out after 120 seconds to {destination}"
            ) from exc
        except OSError as exc:
            raise ScpError(f"Could not execute scp: {exc}") from exc

        if result.returncode != 0:
            raise ScpError(
                f"scp transfer failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )
