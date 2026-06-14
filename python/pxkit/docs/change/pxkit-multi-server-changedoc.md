# pxkit — Multi-Server Support Changedoc

Adds support for multiple Proxmox servers (e.g. T490 + ThinkCentre via
Headscale mesh). The installer discovers VMs automatically from each
server's API. No localhost anywhere — all hosts use mesh IPs.

---

## `src/pxkit/data/pxkit.yaml`

**Why:** `proxmox:` single dict replaced by `servers:` list. Each VM gains
a `server:` key referencing its server by name. Connection hosts are mesh
IPs throughout — no `localhost`. The shipped default is a single-server
example; the installer writes the real user config to `~/.config/pxkit/`.

**BEFORE:**
```yaml
pxkit:
  log_level: normal

  proxmox:
    host: localhost
    port: 8006
    node: wcyjl1
    token_id: carolyn@pam!pxkit

  vms:
    - name: Puppy Linux
      vmid: 100
      connection:
        type: spice
        host: localhost
        port: ~
        security: ~

    - name: Debian XFCE
      vmid: 101
      connection:
        type: spice
        host: localhost
        port: ~
        security: ~

    - name: Rocky Linux
      vmid: 102
      connection:
        type: spice
        host: localhost
        port: ~
        security: ~

    # Mesh VM example (ThinkCentre or other networked host) — uncomment and populate:
    # - name: ThinkCentre Debian
    #   vmid: 203
    #   connection:
    #     type: spice
    #     host: 192.168.x.x
    #     port: ~
    #     security:
    #       method: ssh_tunnel
    #       key: ~/.ssh/keys/thinkcentre/spice
```

**AFTER:**
```yaml
# pxkit.yaml - pxkit default configuration
#
# This file ships with pxkit and provides defaults.
# The installer writes your real config to ~/.config/pxkit/pxkit.yaml.
#
# servers: list of Proxmox hosts. Each needs a unique name.
#   host: mesh IP (Headscale/Tailscale) or LAN IP — no localhost
#   node: Proxmox node name as shown in the web UI
#   token_id: Proxmox API token ID (secret stored in kwallet, never here)
#
# vms: list of VMs across all servers.
#   server: must match a name in the servers list
#   connection.host: same as the server's host — the address SPICE
#                    client connects back to
#
# Connection types:
#   type: spice     SPICE console via remote-viewer
#   type: ssh       SSH terminal (not yet implemented)
#
# Security field:
#   security: ~     direct connection (all current VMs use this)

pxkit:
  log_level: normal

  ui:
    title: System Launcher

  terminal:
    app: xfce4-terminal
    exec_flag: -e

  servers:
    - name: t490
      host: 100.64.0.9
      port: 8006
      node: wcyjl1
      token_id: carolyn@pam!pxkit

  vms:
    - name: Puppy Linux
      vmid: 100
      server: t490
      connection:
        type: spice
        host: 100.64.0.9
        port: ~
        security: ~

    - name: Debian XFCE
      vmid: 101
      server: t490
      connection:
        type: spice
        host: 100.64.0.9
        port: ~
        security: ~

    - name: Rocky Linux
      vmid: 102
      server: t490
      connection:
        type: spice
        host: 100.64.0.9
        port: ~
        security: ~
```

---

## `src/pxkit/config.py`

**Why:** `proxmox` property replaced by `servers` list property and
`get_server(name)` lookup. `ProxmoxConnection` uses `get_server()` to
find the right API endpoint per VM. The old `proxmox` property is removed
entirely — nothing should reference it after this change.

**BEFORE:**
```python
@property
def proxmox(self) -> dict:
    """
    Proxmox connection settings.

    Returns:
        Dict with keys: host, port, node, token_id.
        Token secret is never stored here — retrieve via keyring.
    """
    return self._config.get("proxmox", {})
```

**AFTER:**
```python
@property
def servers(self) -> list:
    """
    List of configured Proxmox servers.

    Returns:
        List of server dicts, each with keys: name, host, port,
        node, token_id. Token secret is never stored here.
    """
    return self._config.get("servers", [])

def get_server(self, name: str) -> dict:
    """
    Look up a server by name.

    Args:
        name: Server name as defined in pxkit.yaml.

    Returns:
        Server dict with keys: name, host, port, node, token_id.

    Raises:
        PxkitConfigError: If no server with that name is found.
    """
    for server in self.servers:
        if server.get("name") == name:
            return server
    available = ", ".join(s.get("name", "?") for s in self.servers)
    raise PxkitConfigError(
        f"Server '{name}' not found in config. "
        f"Available servers: {available}"
    )
```

Also update the module docstring:

**BEFORE (docstring Usage section):**
```python
Usage:
    from pxkit.config import ConfigManager

    config = ConfigManager()
    proxmox = config.proxmox
    vms     = config.vms
```

**AFTER:**
```python
Usage:
    from pxkit.config import ConfigManager

    config = ConfigManager()
    servers = config.servers
    server  = config.get_server("t490")
    vms     = config.vms
```

---

## `src/pxkit/connection.py`

**Why:** `ProxmoxConnection.__init__` previously stored `config.proxmox`
(single dict). Now it stores the full config so it can call
`config.get_server(vm["server"])` per ticket request. The keyring lookup,
URL build, and proxy resolution all use the per-VM server dict rather than
a single shared proxmox config.

**BEFORE (`__init__`):**
```python
def __init__(self, config: ConfigManager):
    self._proxmox = config.proxmox
```

**AFTER (`__init__`):**
```python
def __init__(self, config: ConfigManager):
    self._config = config
```

**BEFORE (`get_spice_ticket` body, after validation):**
```python
    vmid      = vm["vmid"]
    proxy     = self._resolve_proxy(vm)
    url       = self._build_url(f"nodes/{self._proxmox['node']}/qemu/{vmid}/spiceproxy")
    token_id  = self._proxmox["token_id"]
    secret    = self._get_token_secret()
```

**AFTER:**
```python
    server    = self._config.get_server(vm["server"])
    vmid      = vm["vmid"]
    proxy     = self._resolve_proxy(vm)
    url       = self._build_url(server, f"nodes/{server['node']}/qemu/{vmid}/spiceproxy")
    token_id  = server["token_id"]
    secret    = self._get_token_secret(token_id)
```

**BEFORE (`_get_token_secret` signature):**
```python
def _get_token_secret(self) -> str:
    token_id = self._proxmox["token_id"]
    log.debug("Keyring lookup: service='%s' token_id='%s'", _KEYRING_SERVICE, token_id)
    ...
```

**AFTER:**
```python
def _get_token_secret(self, token_id: str) -> str:
    log.debug("Keyring lookup: service='%s' token_id='%s'", _KEYRING_SERVICE, token_id)
    ...
```
(Rest of `_get_token_secret` body is unchanged.)

**BEFORE (`_build_url`):**
```python
def _build_url(self, path: str) -> str:
    host = self._proxmox["host"]
    port = self._proxmox["port"]
    return f"https://{host}:{port}/api2/json/{path}"
```

**AFTER:**
```python
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
```

Also update the module docstring to replace the single-proxmox-block
description with the multi-server explanation:

**BEFORE (docstring, connection strategy section):**
```
The connection type is determined by the VM's connection.type field:
  type: spice     SPICE console via remote-viewer
  type: ssh       SSH terminal (future)

For SPICE VMs, the security field determines the connection strategy:
  security: ~                     direct connection (local VMs)
  security.method: ssh_tunnel     SSH tunnel (mesh/remote VMs, future)
```

**AFTER:**
```
Each VM's 'server' key is used to look up the correct Proxmox API
endpoint from the servers list in config. Token secrets are retrieved
from kwallet via keyring using each server's token_id.

The connection type is determined by the VM's connection.type field:
  type: spice     SPICE console via remote-viewer
  type: ssh       SSH terminal (future)

For SPICE VMs, the security field determines the connection strategy:
  security: ~                     direct connection (all current VMs)
  security.method: ssh_tunnel     SSH tunnel (future)
```

---

## `install.sh`

**Why:** Replaces static keyring/config print instructions (steps 9–10)
with an interactive server configuration loop. For each server: prompts
for name, host, port, node, token_id, and secret; stores the secret in
kwallet; hits the Proxmox API to enumerate QEMU VMs automatically; writes
the full `~/.config/pxkit/pxkit.yaml`. Loops until user enters `q` or
`done`. Everything before step 9 is unchanged.

**BEFORE (steps 9–10 and main):**
```bash
print_keyring_instructions() {
    local install_dir="$1"
    local venv_python="$install_dir/venv/bin/python3"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Final step: store your API token secret"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  pxkit retrieves your Proxmox API token secret from your system"
    echo "  keyring at runtime. Run this command once to store it:"
    echo ""
    echo "    $venv_python -c \\"
    echo "      \"import keyring; keyring.set_password('pxkit', 'YOUR_TOKEN_ID', 'YOUR_TOKEN_SECRET')\""
    echo ""
    echo "  Replace YOUR_TOKEN_ID and YOUR_TOKEN_SECRET with the values from"
    echo "  your Proxmox API token. Example token ID: carolyn@pam!pxkit"
    echo ""
    echo "  Your secret is stored securely in your system keyring (kwallet,"
    echo "  GNOME Keyring, etc.) and never written to disk by pxkit."
    echo ""
}

print_config_instructions() {
    local install_dir="$1"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Configure pxkit"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Copy the default config and edit it with your Proxmox details:"
    echo ""
    echo "    mkdir -p ~/.config/pxkit"
    echo "    cp $install_dir/src/pxkit/data/pxkit.yaml ~/.config/pxkit/pxkit.yaml"
    echo "    \$EDITOR ~/.config/pxkit/pxkit.yaml"
    echo ""
    echo "  Then run pxkit:"
    echo ""
    echo "    pxkit"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

main() {
    print_header
    PYTHON=$(find_python)
    install_virt_viewer
    INSTALL_DIR=$(choose_install_dir)
    check_existing "$INSTALL_DIR"
    download_pxkit "$INSTALL_DIR"
    setup_venv "$INSTALL_DIR" "$PYTHON"
    setup_symlink "$INSTALL_DIR"
    setup_autostart "$INSTALL_DIR/venv/bin/pxkit"
    print_keyring_instructions "$INSTALL_DIR"
    print_config_instructions "$INSTALL_DIR"
    ok "Installation complete."
    echo ""
}
```

**AFTER (steps 9–10 and main):**
```bash
# ---------------------------------------------------------------------------
# Step 9 — Configure servers and discover VMs
# ---------------------------------------------------------------------------

store_keyring_secret() {
    local venv_python="$1"
    local token_id="$2"
    local secret="$3"

    "$venv_python" -c "
import keyring
keyring.set_password('pxkit', '$token_id', '$secret')
" || warn "Keyring store failed for '$token_id'. You can store it manually later."
}

fetch_vms() {
    local host="$1"
    local port="$2"
    local node="$3"
    local token_id="$4"
    local secret="$5"

    curl -sf \
        --insecure \
        -H "Authorization: PVEAPIToken=${token_id}=${secret}" \
        "https://${host}:${port}/api2/json/nodes/${node}/qemu" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', [])
for vm in sorted(data, key=lambda v: v.get('vmid', 0)):
    print(vm['vmid'], vm.get('name', 'unknown'))
"
}

configure_servers() {
    local install_dir="$1"
    local venv_python="$install_dir/venv/bin/python3"
    local user_config_dir="$HOME/.config/pxkit"
    local user_config="$user_config_dir/pxkit.yaml"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Configure Proxmox servers"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Enter each Proxmox server. pxkit will connect to the API"
    echo "  and discover VMs automatically."
    echo "  Enter 'q' or 'done' when finished."
    echo ""

    mkdir -p "$user_config_dir"

    cat > "$user_config" <<'YAML_HEADER'
# pxkit user config — generated by install.sh
# Edit this file to add or remove servers and VMs.
# Re-run install.sh to reconfigure from scratch.

pxkit:
  log_level: normal

  ui:
    title: System Launcher

  terminal:
    app: xfce4-terminal
    exec_flag: -e

  servers:
YAML_HEADER

    local vm_blocks=""

    while true; do
        echo ""
        read -r -p "  Server name (e.g. t490, thinkcentre) or 'q' to finish: " server_name
        case "${server_name,,}" in
            q|done|"") break ;;
        esac

        read -r -p "  Host IP (mesh/LAN address, e.g. 100.64.0.9): " host
        read -r -p "  Port [8006]: " port
        port="${port:-8006}"
        read -r -p "  Node name (as shown in Proxmox UI, e.g. wcyjl1): " node
        read -r -p "  API token ID (e.g. carolyn@pam!pxkit): " token_id
        read -r -s -p "  API token secret: " secret
        echo ""

        cat >> "$user_config" <<YAML_SERVER
    - name: ${server_name}
      host: ${host}
      port: ${port}
      node: ${node}
      token_id: ${token_id}
YAML_SERVER

        store_keyring_secret "$venv_python" "$token_id" "$secret"
        ok "Token secret stored in keyring for '$token_id'."

        info "Connecting to Proxmox API at ${host}:${port} ..."
        local vm_list
        if vm_list=$(fetch_vms "$host" "$port" "$node" "$token_id" "$secret"); then
            local vm_count
            vm_count=$(echo "$vm_list" | grep -c . || true)
            ok "Found ${vm_count} VM(s) on ${server_name}."

            while IFS=" " read -r vmid vm_name; do
                [[ -z "$vmid" ]] && continue
                vm_blocks+=$(cat <<YAML_VM

    - name: ${vm_name}
      vmid: ${vmid}
      server: ${server_name}
      connection:
        type: spice
        host: ${host}
        port: ~
        security: ~
YAML_VM
)
                vm_blocks+=$'\n'
                info "  VM ${vmid}: ${vm_name}"
            done <<< "$vm_list"
        else
            warn "Could not reach Proxmox API at ${host}:${port}."
            warn "Check host, port, node, and token. You can edit ~/.config/pxkit/pxkit.yaml manually."
        fi
    done

    echo "" >> "$user_config"
    echo "  vms:" >> "$user_config"
    if [[ -n "$vm_blocks" ]]; then
        echo "$vm_blocks" >> "$user_config"
    else
        echo "    []" >> "$user_config"
        warn "No VMs were discovered. Edit ~/.config/pxkit/pxkit.yaml to add them manually."
    fi

    echo ""
    ok "Config written to $user_config"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  pxkit is ready. Run:"
    echo ""
    echo "    pxkit"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

main() {
    print_header
    PYTHON=$(find_python)
    install_virt_viewer
    INSTALL_DIR=$(choose_install_dir)
    check_existing "$INSTALL_DIR"
    download_pxkit "$INSTALL_DIR"
    setup_venv "$INSTALL_DIR" "$PYTHON"
    setup_symlink "$INSTALL_DIR"
    setup_autostart "$INSTALL_DIR/venv/bin/pxkit"
    configure_servers "$INSTALL_DIR"
    ok "Installation complete."
    echo ""
}
```

---

## `tests/test_config.py`

**Why:** `proxmox:` key in test fixtures replaced by `servers:` list.
Tests for `config.proxmox` replaced by tests for `config.servers` and
`config.get_server()`. Override tests updated — `servers:` is now a list
replaced wholesale like `vms:`, so the partial-merge port test is removed.

**BEFORE (fixtures):**
```python
MINIMAL_DEFAULT_YAML = textwrap.dedent("""\
    pxkit:
      proxmox:
        host: localhost
        port: 8006
        node: testnode
        token_id: carolyn@pam!pxkit
      terminal:
        app: xfce4-terminal
        exec_flag: -e
      ui:
        title: System Launcher
      vms:
        - name: Puppy Linux
          vmid: 100
          connection:
            type: spice
            host: localhost
            port: ~
            security: ~
""")

USER_OVERRIDE_YAML = textwrap.dedent("""\
    pxkit:
      proxmox:
        host: 192.168.1.100
      vms:
        - name: Remote VM
          vmid: 200
          connection:
            type: spice
            host: 192.168.1.100
            port: ~
            security: ~
""")
```

**AFTER (fixtures):**
```python
MINIMAL_DEFAULT_YAML = textwrap.dedent("""\
    pxkit:
      servers:
        - name: testserver
          host: 100.64.0.9
          port: 8006
          node: testnode
          token_id: carolyn@pam!pxkit
      terminal:
        app: xfce4-terminal
        exec_flag: -e
      ui:
        title: System Launcher
      vms:
        - name: Puppy Linux
          vmid: 100
          server: testserver
          connection:
            type: spice
            host: 100.64.0.9
            port: ~
            security: ~
""")

USER_OVERRIDE_YAML = textwrap.dedent("""\
    pxkit:
      servers:
        - name: remote
          host: 100.64.0.3
          port: 8006
          node: remotenode
          token_id: carolyn@pam!pxkit-remote
      vms:
        - name: Remote VM
          vmid: 200
          server: remote
          connection:
            type: spice
            host: 100.64.0.3
            port: ~
            security: ~
""")
```

**BEFORE (`TestConfigManagerDefaults` — affected tests):**
```python
def test_loads_proxmox_host(self, default_config_file, monkeypatch):
    """Default proxmox host is loaded correctly."""
    ...
    assert config.proxmox["host"] == "localhost"

def test_loads_proxmox_port(self, default_config_file, monkeypatch):
    """Default proxmox port is loaded correctly."""
    ...
    assert config.proxmox["port"] == 8006

def test_vms_empty_when_absent(self, tmp_path, monkeypatch):
    p.write_text("pxkit:\n  proxmox:\n    host: localhost\n", encoding="utf-8")
    ...
    assert config.vms == []
```

**AFTER:**
```python
def test_loads_servers_list(self, default_config_file, monkeypatch):
    """Default servers list is loaded correctly."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
    config = ConfigManager()
    assert len(config.servers) == 1
    assert config.servers[0]["host"] == "100.64.0.9"

def test_loads_server_port(self, default_config_file, monkeypatch):
    """Default server port is loaded correctly."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
    config = ConfigManager()
    assert config.servers[0]["port"] == 8006

def test_get_server_returns_matching_server(self, default_config_file, monkeypatch):
    """get_server() returns the server dict for a known name."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
    config = ConfigManager()
    server = config.get_server("testserver")
    assert server["host"] == "100.64.0.9"
    assert server["token_id"] == "carolyn@pam!pxkit"

def test_get_server_raises_for_unknown_name(self, default_config_file, monkeypatch):
    """get_server() raises PxkitConfigError for an unknown server name."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
    config = ConfigManager()
    with pytest.raises(PxkitConfigError, match="not found in config"):
        config.get_server("nonexistent")

def test_servers_empty_when_absent(self, tmp_path, monkeypatch):
    """servers returns empty list when absent from config."""
    p = tmp_path / "minimal.yaml"
    p.write_text("pxkit:\n  log_level: normal\n", encoding="utf-8")
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", p)
    monkeypatch.setattr("pxkit.config._USER_CONFIG", tmp_path / "nonexistent.yaml")
    config = ConfigManager()
    assert config.servers == []
```

**BEFORE (`TestConfigManagerOverrides` — affected tests):**
```python
def test_user_host_overrides_default(self, default_config_file, user_config_file, monkeypatch):
    """User proxmox host overrides the default."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    config = ConfigManager(config_path=user_config_file)
    assert config.proxmox["host"] == "192.168.1.100"

def test_non_overridden_keys_preserved(self, default_config_file, user_config_file, monkeypatch):
    """Default keys not present in user config are preserved."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    config = ConfigManager(config_path=user_config_file)
    assert config.proxmox["port"] == 8006

def test_no_user_config_uses_defaults(self, default_config_file, tmp_path, monkeypatch):
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    config = ConfigManager(config_path=tmp_path / "nonexistent.yaml")
    assert config.proxmox["host"] == "localhost"
```

**AFTER:**
```python
def test_user_servers_replace_defaults(self, default_config_file, user_config_file, monkeypatch):
    """User servers list replaces default servers list entirely."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    config = ConfigManager(config_path=user_config_file)
    assert len(config.servers) == 1
    assert config.servers[0]["name"] == "remote"
    assert config.servers[0]["host"] == "100.64.0.3"

# test_non_overridden_keys_preserved — REMOVE
# servers is a list, replaced wholesale; partial-merge semantics don't apply.

def test_no_user_config_uses_defaults(self, default_config_file, tmp_path, monkeypatch):
    """Missing user config file falls back to defaults cleanly."""
    monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
    config = ConfigManager(config_path=tmp_path / "nonexistent.yaml")
    assert config.servers[0]["host"] == "100.64.0.9"   # was "localhost"
```

**BEFORE (`TestConfigManagerErrors.test_empty_file_returns_empty_config`):**
```python
def test_empty_file_returns_empty_config(self, tmp_path, monkeypatch):
    ...
    assert config.proxmox == {}
    assert config.vms == []
```

**AFTER:**
```python
def test_empty_file_returns_empty_config(self, tmp_path, monkeypatch):
    ...
    assert config.servers == []   # was config.proxmox == {}
    assert config.vms == []
```

---

## `tests/test_connection.py`

**Why:** `mock_config` fixture previously set `config.proxmox`. Now it
sets `config.servers` and `config.get_server.return_value`. VM fixtures
gain a `server:` key. `_get_token_secret` and `_build_url` take explicit
args now; tests updated accordingly. One new test verifies `get_server`
is called with the correct server name.

**BEFORE (fixtures):**
```python
@pytest.fixture
def mock_config():
    config = MagicMock()
    config.proxmox = {
        "host": "localhost",
        "port": 8006,
        "node": "testnode",
        "token_id": "carolyn@pam!pxkit",
    }
    return config

@pytest.fixture
def spice_vm():
    return {
        "name": "Puppy Linux",
        "vmid": 100,
        "connection": {
            "type": "spice",
            "host": "localhost",
            "port": None,
            "security": None,
        },
    }

@pytest.fixture
def tunnel_vm():
    return {
        "name": "ThinkCentre Debian",
        "vmid": 203,
        "connection": {
            "type": "spice",
            "host": "192.168.1.10",
            "port": None,
            "security": {
                "method": "ssh_tunnel",
                "key": "~/.ssh/keys/thinkcentre/spice",
            },
        },
    }
```

**AFTER (add `_TEST_SERVER` constant, update fixtures):**
```python
_TEST_SERVER = {
    "name": "testserver",
    "host": "100.64.0.9",
    "port": 8006,
    "node": "testnode",
    "token_id": "carolyn@pam!pxkit",
}

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.servers = [_TEST_SERVER]
    config.get_server.return_value = _TEST_SERVER
    return config

@pytest.fixture
def spice_vm():
    return {
        "name": "Puppy Linux",
        "vmid": 100,
        "server": "testserver",
        "connection": {
            "type": "spice",
            "host": "100.64.0.9",
            "port": None,
            "security": None,
        },
    }

@pytest.fixture
def tunnel_vm():
    return {
        "name": "ThinkCentre Debian",
        "vmid": 203,
        "server": "testserver",
        "connection": {
            "type": "spice",
            "host": "100.64.0.3",
            "port": None,
            "security": {
                "method": "ssh_tunnel",
                "key": "~/.ssh/keys/thinkcentre/spice",
            },
        },
    }
```

**BEFORE (`TestResolveProxy.test_local_vm_returns_host`):**
```python
def test_local_vm_returns_host(self, spice_vm):
    result = ProxmoxConnection._resolve_proxy(spice_vm)
    assert result == "localhost"
```

**AFTER:**
```python
def test_local_vm_returns_host(self, spice_vm):
    result = ProxmoxConnection._resolve_proxy(spice_vm)
    assert result == "100.64.0.9"
```

**BEFORE (`TestGetTokenSecret`):**
```python
def test_returns_secret_from_keyring(self, mock_config):
    conn = ProxmoxConnection(mock_config)
    with patch("pxkit.connection.keyring.get_password", return_value="mysecret"):
        result = conn._get_token_secret()
    assert result == "mysecret"

def test_raises_when_secret_not_found(self, mock_config):
    conn = ProxmoxConnection(mock_config)
    with patch("pxkit.connection.keyring.get_password", return_value=None):
        with pytest.raises(PxkitConnectionError, match="not found in keyring"):
            conn._get_token_secret()
```

**AFTER:**
```python
def test_returns_secret_from_keyring(self, mock_config):
    conn = ProxmoxConnection(mock_config)
    with patch("pxkit.connection.keyring.get_password", return_value="mysecret"):
        result = conn._get_token_secret("carolyn@pam!pxkit")
    assert result == "mysecret"

def test_raises_when_secret_not_found(self, mock_config):
    conn = ProxmoxConnection(mock_config)
    with patch("pxkit.connection.keyring.get_password", return_value=None):
        with pytest.raises(PxkitConnectionError, match="not found in keyring"):
            conn._get_token_secret("carolyn@pam!pxkit")
```

**BEFORE (`TestGetSpiceTicket.test_returns_vv_content`):**
```python
def test_returns_vv_content(self, mock_config, spice_vm):
    ...
    assert "[virt-viewer]" in result
    assert "host=localhost" in result
```

**AFTER:**
```python
def test_returns_vv_content(self, mock_config, spice_vm):
    ...
    assert "[virt-viewer]" in result
    assert "host=" in result   # host value comes from API response passthrough
```

**ADD (new test in `TestGetSpiceTicket`):**
```python
def test_uses_correct_server_for_vm(self, mock_config, spice_vm):
    """get_spice_ticket calls get_server with the VM's server key."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": MOCK_SPICE_DATA}
    mock_response.raise_for_status = MagicMock()

    conn = ProxmoxConnection(mock_config)
    with (
        patch("pxkit.connection.keyring.get_password", return_value="mysecret"),
        patch("pxkit.connection.requests.post", return_value=mock_response),
    ):
        conn.get_spice_ticket(spice_vm)

    mock_config.get_server.assert_called_once_with("testserver")
```

---

## Notes

- `test_raises_when_no_keyring_backend` — no change needed. `_get_token_secret`
  still catches `NoKeyringError`; it just takes `token_id` as a parameter now.

- `install.sh` uses `curl` for VM discovery. It's not currently in the
  pre-flight checks. The `fetch_vms` failure path (warn + continue) handles
  it gracefully, but add a `curl` check to `find_python`-style pre-flight
  if you want to be strict.

- LXC containers (600, 601, 700 on ThinkCentre) are not discovered — the
  installer only hits `/qemu`. Add `/lxc` discovery as a future item if needed.

- After install, `~/.config/pxkit/pxkit.yaml` is the live config. The
  shipped `data/pxkit.yaml` is now a schema reference only.
