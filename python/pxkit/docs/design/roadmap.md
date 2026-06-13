# pxkit — Roadmap

Items are roughly sequenced by dependency, not by priority. Earlier items
unblock later ones.

---

## In progress

### Mesh network VM support
The YAML config structure supports remote VMs with SSH tunnel security. The
tunnel setup in `launcher.py` and `connection.py` is not yet implemented.
Local SPICE connections are fully working.

---

## Near term

### SSH terminal launch
`launcher.py` has a `launch_ssh()` stub and the YAML supports `type: ssh`
VM entries. Implementation requires building the SSH command from the VM's
connection config and invoking the configured terminal emulator.

### SSH tunnel for remote SPICE
SPICE connections to mesh network VMs (ThinkCentre and similar) require an
SSH tunnel to be established before the SPICE ticket is retrieved. The
`_resolve_proxy()` logic is in place; the tunnel setup is not.

### Install script
A standalone `install.sh` for Linux that handles:
- Prompting for install location
- Creating a venv and installing dependencies
- Setting up XFCE autostart
- Printing keyring setup instructions

Linux only initially. macOS support follows once RDP path is validated.

---

## Medium term

### Update checker
On startup, fetch a `manifest.fletch` from a known raw GitHub URL and compare
the upstream version against the installed version. Show a non-blocking
notification in the UI if an update is available. Notify only — no auto-update.
Update check runs in a background thread so it never delays launch.

### RDP connection type
Add `type: rdp` to the connection type vocabulary. On macOS, launch via
Microsoft Remote Desktop / Windows App. On Windows, use the built-in RDP
client. Proxmox supports RDP; the launcher needs platform detection and the
right client invocation per OS.

---

## Later

### macOS support
Depends on RDP connection type being implemented and tested. Install script
gains an macOS path using Homebrew for dependencies. Remote-viewer via
Homebrew has not worked reliably; RDP is the intended path.

### Windows support
RDP connection type unblocks this. Install script gains a Windows path.
Keyring backend on Windows uses the Windows Credential Manager — should work
out of the box via the `keyring` library.

### Move to standalone repo
pxkit currently lives in the dev-utils monorepo. Once it is stable and
the install story is clean, it should move to its own repo for clarity
and to simplify the install script URL.

---

## Known limitations

- No SSH terminal launch yet — SSH VM buttons raise "not yet implemented"
- No SSH tunnel setup — remote SPICE VMs require manual tunnel for now
- Linux only — macOS and Windows paths not yet validated
- No update notifications — version checking not yet implemented
