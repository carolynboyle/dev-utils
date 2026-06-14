"""
pxkit.connection - Proxmox API calls and SPICE ticket retrieval.

Handles authentication via Proxmox API token (secret retrieved from
kwallet via keyring at runtime — never stored in config or code),
and retrieves SPICE tickets for VM console access.

Each VM's 'server' key is used to look up the correct Proxmox API
endpoint from the servers list in config. Token secrets are retrieved
from kwallet via keyring using each server's token_id.

The connection type is determined by the VM's connection.type field:
  type: spice     SPICE console via remote-viewer
  type: ssh       SSH terminal (future)

For SPICE VMs, the security field determines the connection strategy:
  security: ~                     direct connection (all current VMs)
  security.method: ssh_tunnel     SSH tunnel (future)

Usage:
    from pxkit.config import ConfigManager
    from pxkit.connection import ProxmoxConnection

    config = ConfigManager()
    conn = ProxmoxConnection(config)
    vv_content = conn.get_spice_ticket(vm)
"""

import logging
import keyring  # pylint: disable=import-error
import requests
import urllib3

from pxkit.config import ConfigManager
from pxkit.exceptions import PxkitConnectionError


# Proxmox uses self-signed certificates by default. Suppress the
# urllib3 warning that would otherwise appear on every request.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Keyring service name under which token secrets are stored.
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

    Each VM specifies which server it belongs to via its 'server' key.
    The correct API endpoint and credentials are looked up per request.

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
        self._config = config

    # -- Public interface -----------------------------------------------------

    def get_spice_ticket(self, vm: dict) -> str:  # pylint: disable=invalid-name
        """
        Retrieve a SPICE ticket for a VM from the Proxmox API.

        Posts to the spiceproxy endpoint and returns the .vv file
        content as a string, ready to be piped to remote-viewer.

        The server is looked up from the VM's 'server' key. The proxy
        address sent to Proxmox is the VM's connection.host — this is
        the address the SPICE client will connect back to.

        Args:
            vm: VM dict from config.vms, with keys: name, vmid, server,
                connection (type, host, port, security).

        Returns:
            SPICE .vv file content as a string.

        Raises:
            PxkitConnectionError: If the connection type is missing or
                                  not 'spice', the API call fails, or
                                  the token secret cannot be retrieved.
            PxkitConfigError: If the VM's server name is not found in config.
        """
        self._validate_connection_type(vm, expected="spice")

        server    = self._config.get_server(vm["server"])
        vmid      = vm["vmid"]
        proxy     = self._resolve_proxy(vm)
        url       = self._build_url(server, f"nodes/{server['node']}/qemu/{vmid}/spiceproxy")
        token_id  = server["token_id"]
        secret    = self._get_token_secret(token_id)

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

        vv_content = self._format_vv(data)
        log.debug("SPICE .vv content for VM %s:\n%s", vmid, vv_content)
        return vv_content

    # -- Internal -------------------------------------------------------------

    @staticmethod
    def _validate_connection_type(vm: dict, expected: str) -> None:  # pylint: disable=invalid-name
        """
        Validate that a VM's connection type matches the expected type.

        Args:
            vm:       VM dict from config.vms.
            expected: The required connection type string (e.g. 'spice').

        Raises:
            PxkitConnectionError: If connection.type is missing or does
                                  not match expected.
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

    def _get_token_secret(self, token_id: str) -> str:
        """
        Retrieve the API token secret from kwallet via keyring.

        Args:
            token_id: Proxmox API token ID to look up.

        Returns:
            Token secret string.

        Raises:
            PxkitConnectionError: If no keyring backend is available,
                                  or the secret is not found in keyring.
        """
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

    @staticmethod
    def _build_url(server: dict, path: str) -> str:
        """
        Build a full Proxmox API URL from a server dict and relative path.

        Args:
            server: Server dict from config (host, port).
            path:   API path relative to /api2/json/ (no leading slash).

        Returns:
            Full URL string.
        """
        host = server["host"]
        port = server["port"]
        return f"https://{host}:{port}/api2/json/{path}"

    @staticmethod
    def _resolve_proxy(vm: dict) -> str:  # pylint: disable=invalid-name
        """
        Determine the proxy address to send to Proxmox spiceproxy.

        This is the address the SPICE client (remote-viewer) will
        connect back to. For direct VMs it is the VM's connection host.
        For SSH tunnel VMs (future) it will be localhost.

        Args:
            vm: VM dict from config.vms.

        Returns:
            Proxy address string.
        """
        security = vm.get("connection", {}).get("security")

        if isinstance(security, dict) and security.get("method") == "ssh_tunnel":
            return "localhost"

        return vm["connection"]["host"]

    @staticmethod
    def _format_vv(data: dict) -> str:
        """
        Format the Proxmox spiceproxy response as a .vv file string.

        Passes the Proxmox API response through as-is. Field names,
        values, and ordering are preserved exactly as returned by the
        Proxmox API. The only addition is the [virt-viewer] header.
        Null values are skipped.

        Args:
            data: Dict of SPICE parameters from the Proxmox API response.

        Returns:
            .vv file content as a string.
        """
        lines = ["[virt-viewer]"]
        for key, value in data.items():
            if value is None:
                continue
            lines.append(f"{key}={value}")
        return "\n".join(lines) + "\n"
