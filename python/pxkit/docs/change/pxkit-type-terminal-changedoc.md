# pxkit — Changedoc: connection type field and terminal config

## Summary

Added `connection.type` field to all VM entries, `terminal` config block
for SSH support, and `_validate_connection_type()` to `connection.py`.
Added `launch_ssh()` stub to `launcher.py`. Added logging to both modules.

---

## src/pxkit/data/pxkit.yaml

### Change 1 — Add `type` field to all VM connection blocks

**Why:** `launcher.py` needs to know whether to invoke `remote-viewer` or
a terminal emulator. Making the type explicit prevents silent misbehaviour
and gives `connection.py` something to validate against.

**BEFORE:**
```yaml
    - name: Puppy Linux
      vmid: 100
      connection:
        host: localhost
        port: ~
        security: ~
```

**AFTER:**
```yaml
    - name: Puppy Linux
      vmid: 100
      connection:
        type: spice
        host: localhost
        port: ~
        security: ~
```

Applied to all three VM entries (Puppy Linux, Debian XFCE, Rocky Linux).

---

### Change 2 — Add `terminal` config block

**Why:** Terminal emulator for SSH connections must be configurable, not
hardcoded. User overrides `app` and `exec_flag` in their
`~/.config/pxkit/pxkit.yaml` to match their installed terminal.

**BEFORE:** *(absent)*

**AFTER:**
```yaml
  terminal:
    app: xfce4-terminal
    exec_flag: -e
```

---

### Change 3 — Update commented examples

**Why:** Examples now reflect the `type` field and show both SPICE tunnel
and SSH terminal patterns.

**BEFORE:**
```yaml
    # Mesh VM example (ThinkCentre or other networked host) — uncomment and populate:
    # - name: ThinkCentre Debian
    #   vmid: 203
    #   connection:
    #     host: 192.168.x.x
    #     port: ~
    #     security:
    #       method: ssh_tunnel
    #       key: ~/.ssh/keys/thinkcentre/spice
```

**AFTER:**
```yaml
    # SPICE over SSH tunnel example (ThinkCentre or other mesh host):
    # - name: ThinkCentre Debian
    #   vmid: 203
    #   connection:
    #     type: spice
    #     host: 192.168.x.x
    #     port: ~
    #     security:
    #       method: ssh_tunnel
    #       key: ~/.ssh/keys/thinkcentre/spice

    # SSH terminal example:
    # - name: ThinkCentre SSH
    #   vmid: ~
    #   connection:
    #     type: ssh
    #     host: 192.168.x.x
    #     user: carolyn
    #     key: ~/.ssh/keys/thinkcentre/ssh
```

---

## src/pxkit/connection.py

### Change 1 — Add `import logging` and logger instance

**Why:** `_validate_connection_type()` logs errors before raising so
failures are captured in the log file as well as surfaced to the caller.

**BEFORE:**
```python
import keyring
import requests
import urllib3
...
_KEYRING_SERVICE = "pxkit"
```

**AFTER:**
```python
import logging
import keyring
import requests
import urllib3
...
_KEYRING_SERVICE = "pxkit"

log = logging.getLogger("pxkit")
```

---

### Change 2 — Add `_validate_connection_type()` static method

**Why:** Catches missing or wrong `connection.type` values early with a
clear error message, rather than failing silently or with a confusing
KeyError later in `get_spice_ticket()`.

**BEFORE:** *(absent)*

**AFTER:**
```python
    @staticmethod
    def _validate_connection_type(vm: dict, expected: str) -> None:
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
```

---

### Change 3 — Call `_validate_connection_type()` at top of `get_spice_ticket()`

**Why:** Validation runs before any API calls are made, so misconfigured
VMs fail fast with a useful message.

**BEFORE:**
```python
        vmid      = vm["vmid"]
        proxy     = self._resolve_proxy(vm)
```

**AFTER:**
```python
        self._validate_connection_type(vm, expected="spice")

        vmid      = vm["vmid"]
        proxy     = self._resolve_proxy(vm)
```

---

## src/pxkit/launcher.py

### Change 1 — Add `import logging` and logger instance

**Why:** `launch_ssh()` stub logs a warning; future methods will log
launch success/failure.

**BEFORE:**
```python
import subprocess
...
from pxkit.exceptions import PxkitLaunchError
```

**AFTER:**
```python
import logging
import subprocess
...
from pxkit.exceptions import PxkitLaunchError

log = logging.getLogger("pxkit")
```

---

### Change 2 — Store terminal config in `__init__`

**Why:** `launch_ssh()` needs `terminal.app` and `terminal.exec_flag`
from config. Stored at init alongside `_proxmox` for consistency.

**BEFORE:**
```python
        self._proxmox = config.proxmox
```

**AFTER:**
```python
        self._proxmox  = config.proxmox
        self._terminal = config.get("terminal", {})
```

---

### Change 3 — Add `launch_ssh()` stub

**Why:** Defines the interface and confirms the config shape is correct
before SSH implementation begins. Raises clearly rather than silently
doing nothing if called prematurely.

**BEFORE:** *(absent)*

**AFTER:**
```python
    def launch_ssh(self, vm: dict) -> None:
        name = vm.get("name", vm.get("vmid", "unknown"))
        log.warning("launch_ssh called for '%s' but SSH launch is not yet implemented.", name)
        raise PxkitLaunchError(
            f"SSH launch for '{name}' is not yet implemented."
        )
```
