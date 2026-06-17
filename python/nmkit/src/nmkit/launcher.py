"""
nmkit.launcher - NoMachine session launcher for nmkit.

Generates a temporary .nxs session file from a built-in XML template,
populating the host, port, and username from the connection config, then
launches nxclient with the generated file.

The .nxs template is derived from a real exported NoMachine session file
and contains only the fields nxclient requires. Fields that contain
machine-specific or sensitive data (Node UUID, Auth, Session screenshot)
are intentionally omitted so that NoMachine prompts for credentials and
negotiates a fresh session.

Usage:
    from nmkit.launcher import Launcher

    launcher = Launcher(config)
    launcher.launch(connection)
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from string import Template

from nmkit.exceptions import NmkitLaunchError

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# .nxs XML template
# ---------------------------------------------------------------------------
# Derived from a real exported session file. Only the minimal required fields
# are included. $SERVER_HOST, $SERVER_PORT, and $USER are substituted at
# launch time from the connection config. Auth and Node UUID are omitted
# so that NoMachine handles authentication itself.

_NXS_TEMPLATE = Template("""\
<!DOCTYPE NXClientSettings>
<NXClientSettings version="2.3" application="nxclient" >
 <group name="Advanced" >
  <option key="Enable remote cursor tracking" value="" />
  <option key="Disable updating clipboard on mouse selection" value="false" />
  <option key="Grab keyboard input" value="" />
  <option key="Grab mouse input" value="" />
  <option key="Enable HTTP proxy" value="false" />
  <option key="HTTP proxy host" value="" />
  <option key="HTTP proxy port" value="8080" />
  <option key="HTTP proxy password" value="EMPTY_PASSWORD" />
  <option key="Remember HTTP proxy password" value="false" />
  <option key="HTTP proxy username" value="" />
  <option key="Emulate middle mouse button" value="" />
  <option key="Use TOR for SOCKS proxy connections" value="false" />
  <option key="Use URL for automatic proxy configuration" value="false" />
  <option key="Manual proxy configuration type" value="http" />
  <option key="Proxy configuration mode" value="automatic" />
  <option key="Automatic proxy configuration URL" value="" />
  <option key="Swap Control and Command modifiers" value="false" />
 </group>
 <group name="Environment" >
  <option key="Use font server" value="false" />
  <option key="Font server host" value="" />
  <option key="Font server port" value="7100" />
 </group>
 <group name="General" >
  <option key="Automatically accept new hosts identification key" value="true" />
  <option key="Connection request greeting message" value="" />
  <option key="Automatically connect to session with specified ID" value="" />
  <option key="Enable session auto-resize" value="" />
  <option key="Physical desktop auto-resize" value="false" />
  <option key="Virtual desktop auto-resize" value="false" />
  <option key="Close the client application when a single session terminates" value="" />
  <option key="Connection service" value="nx" />
  <option key="Always create a physical desktop on a headless Linux host" value="false" />
  <option key="View a specific monitor among available monitors" value="0" />
  <option key="Command line" value="" />
  <option key="Use custom server" value="false" />
  <option key="Custom server command" value="/etc/NX/nxserver" />
  <option key="Custom Unix Desktop" value="" />
  <option key="NoMachine daemon port" value="4000" />
  <option key="Connect to this node when manual selection is enabled" value="" />
  <option key="Connect to this server when manual selection is enabled" value="" />
  <option key="Desktop" value="" />
  <option key="Disable SHM" value="false" />
  <option key="Disable emulate shared pixmaps" value="false" />
  <option key="Use render" value="true" />
  <option key="Try to wake up server when it is powered off" value="false" />
  <option key="Link quality" value="5" />
  <option key="Node UUID" value="" />
  <option key="Recently connected nodes" value="" />
  <option key="Physical desktop resize mode" value="scaled" />
  <option key="Session resize mode" value="" />
  <option key="Virtual desktop resize mode" value="viewport" />
  <option key="Server MAC address" value="" />
  <option key="Resize the remote screen upon connecting" value="no" />
  <option key="Resolution" value="" />
  <option key="Use WebRTC for multimedia data" value="true" />
  <option key="Save connection request greeting message" value="false" />
  <option key="Remember session window size and position" value="" />
  <option key="Remember password" value="false" />
  <option key="Remember username" value="true" />
  <option key="Server hardware" value="" />
  <option key="Server host" value="$SERVER_HOST" />
  <option key="Server port" value="$SERVER_PORT" />
  <option key="Server product" value="NoMachine" />
  <option key="Server product version" value="" />
  <option key="Server hardware specifications" value="" />
  <option key="Session" value="" />
  <option key="Show connection request greeting message panel" value="true" />
  <option key="Show expiring license warning message" value="true" />
  <option key="Show remote audio alert message" value="false" />
  <option key="Show remote display resize message" value="false" />
  <option key="Show remote desktop view mode message" value="false" />
  <option key="UDP communication port" value="" />
  <option key="Use UDP communication for multimedia data" value="true" />
  <option key="Use specific port for UDP communication" value="false" />
  <option key="Virtual desktop" value="false" />
  <option key="VPN mode" value="tunnel" />
  <option key="Enable VPN kill switch" value="false" />
  <option key="NoMachine web server port" value="4443" />
  <option key="Web session information token" value="" />
  <option key="Session window geometry" value="" />
  <option key="Session window state" value="normal" />
  <option key="xdm mode" value="" />
  <option key="xdm broadcast port" value="177" />
  <option key="xdm list host" value="localhost" />
  <option key="xdm list port" value="177" />
  <option key="xdm query host" value="localhost" />
  <option key="xdm query port" value="177" />
  <option key="Use custom resolution" value="false" />
  <option key="Resolution width" value="" />
  <option key="Resolution height" value="" />
 </group>
 <group name="Login" >
  <option key="Always use selected user login" value="false" />
  <option key="Alternate NX Key" value="" />
  <option key="Forward SSH authentication" value="false" />
  <option key="Guest Mode" value="false" />
  <option key="Guest password" value="" />
  <option key="Guest username" value="" />
  <option key="Guest server" value="" />
  <option key="Guest desktop sharing mode" value="false" />
  <option key="Last selected user login" value="system user" />
  <option key="Server authentication method" value="system" />
  <option key="User" value="$USER" />
  <option key="Wallix login" value="" />
  <option key="NX login method" value="password" />
  <option key="Private key for NX authentication" value="" />
  <option key="Use alternate smart card module" value="false" />
  <option key="Smart card authentication module" value="" />
  <option key="Private key" value="" />
  <option key="Public Key" value="" />
  <option key="System auth" value="EMPTY_PASSWORD" />
  <option key="Two-factor authentication password" value="EMPTY_PASSWORD" />
  <option key="Remember NoMachine password" value="false" />
  <option key="Remember two-factor authentication password" value="false" />
  <option key="Imported private key for NX authentication" value="" />
  <option key="Use imported private key for NX authentication" value="false" />
  <option key="Imported private key" value="" />
  <option key="Use imported private key" value="false" />
  <option key="NoMachine Network login code" value="EMPTY_PASSWORD" />
  <option key="Remember NoMachine Network access ID" value="false" />
  <option key="NoMachine Network access ID" value="EMPTY_PASSWORD" />
  <option key="System login method" value="password" />
  <option key="Use alternate NX Key" value="false" />
  <option key="GSSAPI subsystem for the kerberos authentication" value="kerberos" />
  <option key="Kerberos key exchange to identify server host" value="false" />
  <option key="DNS translation when passing server to Kerberos library" value="false" />
 </group>
 <group name="Images" >
  <option key="Disable network-adaptive quality" value="false" />
  <option key="Disable backingstore" value="false" />
  <option key="Disable composite" value="false" />
  <option key="Disable image post-processing" value="false" />
  <option key="Disable frame buffering on decoding" value="false" />
  <option key="Disable lossless display refinement" value="false" />
  <option key="Disable multi-pass display encoding" value="false" />
  <option key="E-reader display update policy" value="false" />
  <option key="Video frame rate for display server" value="30" />
  <option key="Stream downsampling factor" value="0" />
  <option key="Request a specific frame rate" value="false" />
  <option key="Video encoding quality" value="5" />
 </group>
 <group name="Services" >
  <option key="Output audio device" value="autodetect" />
  <option key="Output audio quality" value="5" />
  <option key="Audio" value="true" />
  <option key="IPPPrinting" value="true" />
  <option key="Enable devices sharing" value="true" />
  <option key="Shares" value="true" />
  <option key="Mute audio of the remote physical desktop" value="true" />
  <option key="Input voice device" value="autodetect" />
  <option key="Input voice quality" value="5" />
 </group>
 <group name="VNC Session" >
  <option key="Display" value=":0" />
  <option key="Password" value="EMPTY_PASSWORD" />
  <option key="Remember login credentials" value="false" />
  <option key="Remember" value="false" />
  <option key="Server" value="" />
 </group>
 <group name="Windows Session" >
  <option key="Application" value="" />
  <option key="Authentication" value="2" />
  <option key="Domain" value="" />
  <option key="Password" value="EMPTY_PASSWORD" />
  <option key="Remember login credentials" value="false" />
  <option key="Remember" value="false" />
  <option key="Run application" value="false" />
  <option key="Server" value="" />
  <option key="User" value="" />
 </group>
 <group name="Remote Session" >
  <option key="Host" value="" />
  <option key="Port" value="" />
  <option key="Username" value="" />
  <option key="Password" value="EMPTY_PASSWORD" />
  <option key="Remember login credentials" value="false" />
  <option key="Fingerprint" value="" />
 </group>
</NXClientSettings>
""")


# ---------------------------------------------------------------------------
# Launcher
# ---------------------------------------------------------------------------

class Launcher:  # pylint: disable=too-few-public-methods
    """
    Generates temporary .nxs session files and launches nxclient.

    The nxclient binary path is read from the app config. Each launch
    writes a temporary .nxs file, passes it to nxclient, and removes it
    once nxclient has started (nxclient reads the file at startup and does
    not need it to persist).

    Usage:
        launcher = Launcher(config)
        launcher.launch(connection)
    """

    def __init__(self, config):
        """
        Initialise Launcher.

        Args:
            config: A ConfigManager instance. Used to read the nxclient
                    binary path from config.app['nxclient'].
        """
        self._nxclient = config.app.get("nxclient", "/usr/NX/bin/nxclient")

    def launch(self, connection: dict) -> None:
        """
        Launch a NoMachine session for the given connection.

        Writes a temporary .nxs file populated from the connection dict,
        then starts nxclient as a detached subprocess. The temp file is
        removed after nxclient starts.

        Args:
            connection: A connection dict with keys: name, host, port,
                        user, os.

        Raises:
            NmkitLaunchError: If the nxclient binary is not found or
                              fails to start.
        """
        nxs_content = self._render_nxs(connection)
        nxs_path    = self._write_temp_nxs(nxs_content)

        try:
            self._start_nxclient(nxs_path)
        finally:
            # Always clean up the temp file, even if launch fails.
            try:
                nxs_path.unlink()
            except OSError as exc:
                log.warning("Could not remove temp .nxs file %s: %s", nxs_path, exc)

    # -- Internal -------------------------------------------------------------

    def _render_nxs(self, connection: dict) -> str:
        """
        Render the .nxs XML template for the given connection.

        Args:
            connection: Connection dict with host, port, user keys.

        Returns:
            Rendered .nxs XML string.
        """
        return _NXS_TEMPLATE.substitute(
            SERVER_HOST=connection["host"],
            SERVER_PORT=connection["port"],
            USER=connection["user"],
        )

    @staticmethod
    def _write_temp_nxs(content: str) -> Path:
        """
        Write .nxs content to a temporary file and return its path.

        The file is created in the system temp directory with a .nxs
        suffix and is not auto-deleted (caller is responsible for cleanup).

        Args:
            content: The .nxs XML string to write.

        Returns:
            Path to the written temp file.

        Raises:
            NmkitLaunchError: If the temp file cannot be written.
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".nxs",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                return Path(tmp.name)
        except OSError as exc:
            raise NmkitLaunchError(
                f"Could not write temporary .nxs file: {exc}"
            ) from exc

    def _start_nxclient(self, nxs_path: Path) -> None:
        """
        Start nxclient as a detached subprocess with the given .nxs file.

        Args:
            nxs_path: Path to the .nxs session file.

        Raises:
            NmkitLaunchError: If nxclient cannot be found or started.
        """
        cmd = [self._nxclient, "--session", str(nxs_path)]
        log.info("Launching: %s", " ".join(cmd))

        try:
            subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise NmkitLaunchError(
                f"nxclient not found at {self._nxclient!r}. "
                "Check the 'nxclient' path in nmkit.yaml."
            ) from exc
        except OSError as exc:
            raise NmkitLaunchError(
                f"Failed to start nxclient: {exc}"
            ) from exc

        log.info(
            "nxclient started for %s (%s)",
            nxs_path.name,
            self._nxclient,
        )
