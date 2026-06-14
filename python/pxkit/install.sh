#!/usr/bin/env bash
# install.sh — pxkit installer
#
# Usage:
#   bash install.sh
#
# Or via curl:
#   curl -sSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/python/pxkit/install.sh | bash
#
# Installs pxkit to a directory of your choice, creates a venv, installs
# dependencies, optionally sets up XFCE autostart, and symlinks the pxkit
# command to ~/.local/bin/.
#
# Safe to re-run — prompts before overwriting an existing installation.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_URL="https://github.com/carolynboyle/dev-utils.git"
PACKAGE_SUBDIR="python/pxkit"
DEFAULT_INSTALL_DIR="$HOME/.local/share/pxkit"
SYMLINK_DIR="$HOME/.local/bin"
SYMLINK_PATH="$SYMLINK_DIR/pxkit"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/pxkit.desktop"
MIN_PYTHON_MINOR=11

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  pxkit installer"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

info()    { echo "  [info]  $*" >&2; }
ok()      { echo "  [ ok ]  $*" >&2; }
warn()    { echo "  [warn]  $*" >&2; }
die()     { echo "  [fail]  $*" >&2; exit 1; }

prompt_yn() {
    # Usage: prompt_yn "Question" "y|n" → returns 0 for yes, 1 for no
    local question="$1"
    local default="${2:-n}"
    local prompt

    if [[ "$default" == "y" ]]; then
        prompt="[Yn]"
    else
        prompt="[yN]"
    fi

    while true; do
        read -r -p "  $question $prompt " answer
        answer="${answer:-$default}"
        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no)  return 1 ;;
            *)     echo "  Please answer y or n." ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# Step 1 — Find Python 3.11+
# ---------------------------------------------------------------------------

find_python() {
    info "Looking for Python 3.11+..."

    local best_python=""
    local best_minor=0

    # Check python3.11, python3.12, python3.13, python3.14, then python3
    for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local minor
            minor=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
            local major
            major=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)

            if [[ "$major" -eq 3 && "$minor" -ge "$MIN_PYTHON_MINOR" && "$minor" -gt "$best_minor" ]]; then
                best_python="$candidate"
                best_minor="$minor"
            fi
        fi
    done

    if [[ -z "$best_python" ]]; then
        die "Python 3.$MIN_PYTHON_MINOR or newer is required but was not found. Install it and re-run."
    fi

    local version
    version=$("$best_python" --version 2>&1)
    ok "Found $version ($best_python)"
    echo "$best_python"
}

# ---------------------------------------------------------------------------
# Step 2 — Install virt-viewer
# ---------------------------------------------------------------------------

install_virt_viewer() {
    if command -v remote-viewer &>/dev/null; then
        ok "virt-viewer already installed."
        return
    fi

    info "virt-viewer not found. Attempting to install..."

    if command -v apt &>/dev/null; then
        sudo apt install -y virt-viewer
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y virt-viewer
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm virt-viewer
    else
        warn "Could not detect package manager. Install virt-viewer manually before using pxkit."
        warn "  Debian/Ubuntu: sudo apt install virt-viewer"
        warn "  Fedora/Rocky:  sudo dnf install virt-viewer"
        warn "  Arch:          sudo pacman -S virt-viewer"
        return
    fi

    ok "virt-viewer installed."
}

# ---------------------------------------------------------------------------
# Step 3 — Choose install location
# ---------------------------------------------------------------------------

choose_install_dir() {
    echo "" >&2
    echo "  Where would you like to install pxkit?" >&2
    echo "  Press Enter to accept the default." >&2
    echo "" >&2
    read -r -p "  Install location [$DEFAULT_INSTALL_DIR]: " install_dir <&1
    install_dir="${install_dir:-$DEFAULT_INSTALL_DIR}"

    # Expand tilde if present
    install_dir="${install_dir/#\~/$HOME}"

    echo "$install_dir"
}

# ---------------------------------------------------------------------------
# Step 4 — Check for existing installation
# ---------------------------------------------------------------------------

check_existing() {
    local install_dir="$1"

    if [[ -d "$install_dir" ]]; then
        warn "An existing installation was found at $install_dir."
        if ! prompt_yn "This will overwrite the existing installation. Continue?" "n"; then
            echo ""
            info "Installation cancelled."
            exit 0
        fi
        info "Removing existing installation..."
        rm -rf "$install_dir"
    fi
}

# ---------------------------------------------------------------------------
# Step 5 — Download pxkit
# ---------------------------------------------------------------------------

download_pxkit() {
    local install_dir="$1"

    info "Downloading pxkit..."

    if command -v git &>/dev/null; then
        # Sparse checkout — only pull python/pxkit, not the whole monorepo
        mkdir -p "$install_dir"
        git clone \
            --no-checkout \
            --depth=1 \
            --filter=blob:none \
            "$REPO_URL" \
            "$install_dir/repo" 2>/dev/null

        cd "$install_dir/repo"
        git sparse-checkout set "$PACKAGE_SUBDIR"
        git checkout 2>/dev/null

        # Move package contents up and clean up repo scaffolding
        cp -r "$install_dir/repo/$PACKAGE_SUBDIR/." "$install_dir/"
        rm -rf "$install_dir/repo"
        cd "$install_dir"
    else
        die "git is required for installation. Install git and re-run."
    fi

    ok "pxkit downloaded to $install_dir."
}

# ---------------------------------------------------------------------------
# Step 6 — Create venv and install dependencies
# ---------------------------------------------------------------------------

setup_venv() {
    local install_dir="$1"
    local python="$2"

    info "Creating virtual environment..."
    "$python" -m venv "$install_dir/venv"
    ok "Virtual environment created."

    info "Installing pxkit and dependencies..."
    "$install_dir/venv/bin/pip" install --quiet -e "$install_dir"
    ok "Dependencies installed."
}

# ---------------------------------------------------------------------------
# Step 7 — Symlink to ~/.local/bin
# ---------------------------------------------------------------------------

setup_symlink() {
    local install_dir="$1"
    local venv_pxkit="$install_dir/venv/bin/pxkit"

    mkdir -p "$SYMLINK_DIR"

    if [[ -L "$SYMLINK_PATH" ]]; then
        info "Removing existing symlink at $SYMLINK_PATH."
        rm "$SYMLINK_PATH"
    elif [[ -e "$SYMLINK_PATH" ]]; then
        warn "$SYMLINK_PATH exists and is not a symlink — leaving it alone."
        warn "Add $install_dir/venv/bin to your PATH manually."
        return
    fi

    ln -s "$venv_pxkit" "$SYMLINK_PATH"
    ok "Symlink created: $SYMLINK_PATH → $venv_pxkit"

    # Check ~/.local/bin is on PATH
    if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
        warn "$SYMLINK_DIR is not on your PATH."
        warn "Add this to your ~/.bashrc or ~/.zshrc:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# ---------------------------------------------------------------------------
# Step 8 — XFCE autostart
# ---------------------------------------------------------------------------

setup_autostart() {
    local venv_pxkit="$1"

    echo ""
    if ! prompt_yn "Set up pxkit to launch automatically on login?" "n"; then
        info "Skipping autostart setup."
        return
    fi

    mkdir -p "$AUTOSTART_DIR"

    cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=pxkit
Exec=$venv_pxkit
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Proxmox VM launcher
EOF

    ok "Autostart entry created at $AUTOSTART_FILE."
}

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
        read -r -p "  Server name (e.g. homeserver, officeserver) or 'q' to finish: " server_name
        case "${server_name,,}" in
            q|done|"") break ;;
        esac
        if [[ -z "$server_name" ]]; then
            warn "Server name cannot be empty."
            continue
        fi

        while true; do
            read -r -p "  Host IP (mesh/LAN address, e.g. 192.168.1.100): " host
            [[ -n "$host" ]] && break
            warn "Host IP cannot be empty."
        done

        read -r -p "  Port [8006]: " port
        port="${port:-8006}"

        while true; do
            read -r -p "  Node name (as shown in Proxmox web UI, e.g. pve): " node
            [[ -n "$node" ]] && break
            warn "Node name cannot be empty."
        done

        while true; do
            read -r -p "  API token ID (e.g. root@pam!mytoken): " token_id
            [[ -n "$token_id" ]] && break
            warn "Token ID cannot be empty."
        done

        while true; do
            read -r -s -p "  API token secret: " secret
            echo ""
            [[ -n "$secret" ]] && break
            warn "Token secret cannot be empty."
        done

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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    # Handle --wipe: remove everything and continue into fresh install
    local wipe=false
    for arg in "$@"; do
        if [[ "$arg" == "--wipe" ]]; then
            wipe=true
        fi
    done

    print_header

    PYTHON=$(find_python)
    install_virt_viewer
    INSTALL_DIR=$(choose_install_dir)

    if [[ "$wipe" == true ]]; then
        info "Wiping existing installation..."
        rm -rf "$INSTALL_DIR"
        local user_config="$HOME/.config/pxkit/pxkit.yaml"
        if [[ -f "$user_config" ]]; then
            rm -f "$user_config"
            ok "Removed $user_config"
        fi
        ok "Wipe complete. Reinstalling..."
    else
        check_existing "$INSTALL_DIR"
    fi
    download_pxkit "$INSTALL_DIR"
    setup_venv "$INSTALL_DIR" "$PYTHON"
    setup_symlink "$INSTALL_DIR"
    setup_autostart "$INSTALL_DIR/venv/bin/pxkit"

    configure_servers "$INSTALL_DIR"

    ok "Installation complete."
    echo ""
}

main "$@"
