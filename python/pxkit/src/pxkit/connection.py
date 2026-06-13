"""
pxkit.connection - Proxmox API calls and SPICE ticket retrieval.

Handles authentication via Proxmox API token (secret retrieved from
kwallet via keyring at runtime — never stored in config or code),
and retrieves SPICE tickets for VM console access.

The connection type is determined by the VM's connection.type field:
  type: spice     SPICE console via remote-viewer
  type: ssh       SSH terminal (future)

For SPICE VMs, the security field determines the connection strategy:
  security: ~                     direct connection (local VMs)
  security.method: ssh_tunnel     SSH tunnel (mesh/remote VMs, future)

Usage:
    from pxkit.config import ConfigManager
    from pxkit.connection import ProxmoxConnection

    config = ConfigManager()
    conn = ProxmoxConnection(config)
    vv_content = conn.get_spice_ticket(vm)
"""

import logging
import keyring
import requests
import urllib3

from pxkit.config import ConfigManager
from pxkit.exceptions import PxkitConnectionError


# Proxmox uses self-signed certificates by default. Suppress the
# urllib3 warning that would otherwise appear on every request.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Keyring service name under which the token secret is stored.
_KEYRING_SERVICE = "pxkit"

log = logging.getLogger("pxkit")


# ---------------------------------------------------------------------------
# ProxmoxConnection
# ---------------------------------------------------------------------------

class ProxmoxConnection:  # pylint: disable=too-few-public-methods
    """
    Handles Proxmox API authentication and SPICE ticket retrieval.

    Authenticates using a Proxmox API token. The token secret is
    retrieved from kwallet via keyring at runtime — it is never stored
    in config files or code.

    Usage:
        conn = ProxmoxConnection(config)
        vv_content = conn.get_spice_ticket(vm)
    """

    def __init__(self, config: ConfigManager):
        """
        Initialise ProxmoxConnection.

        Args:
            config: Loaded ConfigManager instance.
        """
        self._proxmox = config.proxmox

    # -- Public interface -----------------------------------------------------

    def get_spice_ticket(self, vm: dict) -> str:
        """
        Retrieve a SPICE ticket for a VM from the Proxmox API.

        Posts to the spiceproxy endpoint and returns the .vv file
        content as a string, ready to be written to a temp file and
        passed to remote-viewer.

        The proxy address sent to Proxmox is derived from the VM's
        connection.host — this is the address the SPICE client will
        connect back to. For local VMs this matches the Proxmox host.
        For SSH tunnel VMs (future) this will be localhost.

        Args:
            vm: VM dict from config.vms, with keys: name, vmid,
                connection (type, host, port, security).

        Returns:
            SPICE .vv file content as a string.

        Raises:
            PxkitConnectionError: If the connection type is missing or
                                  not 'spice', the API call fails, or
                                  the token secret cannot be retrieved.
        """
        self._validate_connection_type(vm, expected="spice")

        vmid      = vm["vmid"]
        proxy     = self._resolve_proxy(vm)
        url       = self._build_url(f"nodes/{self._proxmox['node']}/qemu/{vmid}/spiceproxy")
        token_id  = self._proxmox["token_id"]
        secret    = self._get_token_secret()

        headers = {
            "Authorization": f"PVEAPIToken={token_id}={secret}",
        }

        log.debug("SPICE ticket request: POST %s (proxy=%s)", url, proxy)

        try:
            response = requests.post(
                url,
                headers=headers,
                data={"proxy": proxy},
                verify=False,
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise PxkitConnectionError(
                f"Failed to retrieve SPICE ticket for VM {vmid}: {exc}"
            ) from exc

        data = response.json().get("data")
        if not data:
            raise PxkitConnectionError(
                f"Proxmox API returned no data for VM {vmid}. "
                f"Check that the VM is running and the token has PVEVMUser on /vms."
            )

        vv_content = self._format_vv(data, vm["connection"]["type"])
        log.debug("SPICE .vv content for VM %s:\n%s", vmid, vv_content)
        return vv_content

    # -- Internal -------------------------------------------------------------

    @staticmethod
    def _validate_connection_type(vm: dict, expected: str) -> None:
        """
        Validate that a VM's connection type matches the expected type.

        Args:
            vm:       VM dict from config.vms.
            expected: The required connection type string (e.g. 'spice').

        Raises:
            PxkitConnectionError: If connection.type is missing or does
                                  not match expected. Error is also logged.
        """
        conn_type = vm.get("connection", {}).get("type")
        name = vm.get("name", vm.get("vmid", "unknown"))

        if conn_type is None:
            msg = (
                f"VM '{name}' has no connection.type defined. "
                f"Add 'type: {expected}' to its connection block in pxkit.yaml."
            )
            log.error(msg)
            raise PxkitConnectionError(msg)

        if conn_type != expected:
            msg = (
                f"VM '{name}' has connection.type '{conn_type}' "
                f"but expected '{expected}'."
            )
            log.error(msg)
            raise PxkitConnectionError(msg)

    def _get_token_secret(self) -> str:
        """
        Retrieve the API token secret from kwallet via keyring.

        Returns:
            Token secret string.

        Raises:
            PxkitConnectionError: If no keyring backend is available,
                                  or the secret is not found in keyring.
        """
        token_id = self._proxmox["token_id"]
        log.debug("Keyring lookup: service='%s' token_id='%s'", _KEYRING_SERVICE, token_id)

        try:
            secret = keyring.get_password(_KEYRING_SERVICE, token_id)
        except keyring.errors.NoKeyringError as exc:
            raise PxkitConnectionError(
                "No keyring backend available. "
                "Is kwalletd5 running and registered on D-Bus?"
            ) from exc

        if secret is None:
            raise PxkitConnectionError(
                f"Token secret for '{token_id}' not found in keyring service "
                f"'{_KEYRING_SERVICE}'. "
                f"Store it with: keyring.set_password('{_KEYRING_SERVICE}', "
                f"'{token_id}', '<secret>')"
            )

        log.debug("Keyring lookup: secret found for '%s'.", token_id)
        return secret

    def _build_url(self, path: str) -> str:
        """
        Build a full Proxmox API URL from a relative path.

        Args:
            path: API path relative to /api2/json/ (no leading slash).

        Returns:
            Full URL string.
        """
        host = self._proxmox["host"]
        port = self._proxmox["port"]
        return f"https://{host}:{port}/api2/json/{path}"

    @staticmethod
    def _resolve_proxy(vm: dict) -> str:
        """
        Determine the proxy address to send to Proxmox spiceproxy.

        This is the address the SPICE client (remote-viewer) will
        connect back to. For local VMs it is the VM's connection host.
        For SSH tunnel VMs (future) it will be localhost.

        Args:
            vm: VM dict from config.vms.

        Returns:
            Proxy address string.
        """
        security = vm.get("connection", {}).get("security")

        if security is None:
            # Local VM — connect directly to the host
            return vm["connection"]["host"]

        if isinstance(security, dict) and security.get("method") == "ssh_tunnel":
            # SSH tunnel — SPICE client connects to the local tunnel endpoint
            return "localhost"

        return vm["connection"]["host"]

    @staticmethod
    def _format_vv(data: dict, conn_type: str) -> str:
        """
        Format the Proxmox spiceproxy response as a .vv file string.

        Proxmox returns the SPICE connection parameters as a dict.
        remote-viewer expects them as a .vv (virt-viewer) config file.

        Fixes applied:
        - Adds 'type=<conn_type>' from the VM's connection config
          (Proxmox does not include it in the response)
        - Unescapes '\\n' in the 'ca' field to real newlines
        - Skips the 'proxy' field (Proxmox returns its own proxy value
          which is not relevant to the SPICE client)

        Args:
            data:      Dict of SPICE parameters from the Proxmox API response.
            conn_type: Connection type string from the VM config (e.g. 'spice').

        Returns:
            .vv file content as a string.
        """
        # Keys to skip — not valid in .vv files or cause remote-viewer issues
        skip_keys = {"proxy"}

        lines = ["[virt-viewer]", f"type={conn_type}"]
        for key, value in data.items():
            if key in skip_keys or value is None:
                continue
            # Fix escaped newlines in the CA certificate
            if key == "ca" and isinstance(value, str):
                value = value.replace("\\n", "\n")
            lines.append(f"{key}={value}")
        return "\n".join(lines) + "\n"
