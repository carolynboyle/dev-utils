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

info()    { echo "  [info]  $*"; }
ok()      { echo "  [ ok ]  $*"; }
warn()    { echo "  [warn]  $*"; }
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
    # Use global — avoids stdout capture bug when called with $(...)
    PYTHON="$best_python"
}

# ---------------------------------------------------------------------------
# Step 2 — Install system dependencies
# ---------------------------------------------------------------------------
#
# System packages required by pxkit (keep in sync with docs/system-footprint.md):
#
#   libxcb-cursor0      Qt 6.5+ xcb platform plugin
#   python3-secretstorage  keyring SecretService backend
#   libsecret-1-0       secretstorage runtime dependency
#
# virt-viewer is handled separately below as it has its own multi-distro logic.

install_system_deps() {
    info "Installing system dependencies..."

    if command -v apt &>/dev/null; then
        sudo apt-get install -y \
            libxcb-cursor0 \
            python3-secretstorage \
            libsecret-1-0
    elif command -v dnf &>/dev/null; then
        # Package names differ on Fedora/Rocky — secretstorage is pip-only there
        sudo dnf install -y \
            libxcb-cursor
        warn "secretstorage: install via pip (included in venv dependencies)."
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm \
            libxcb \
            python-secretstorage
    else
        warn "Could not detect package manager. Install these manually:"
        warn "  Debian/Ubuntu: sudo apt install libxcb-cursor0 python3-secretstorage libsecret-1-0"
        warn "  Fedora/Rocky:  sudo dnf install libxcb-cursor"
        warn "  Arch:          sudo pacman -S libxcb python-secretstorage"
    fi

    ok "System dependencies installed."
}

# ---------------------------------------------------------------------------
# Step 3 — Install virt-viewer
# ---------------------------------------------------------------------------

install_virt_viewer() {
    if command -v remote-viewer &>/dev/null; then
        ok "virt-viewer already installed."
        return
    fi

    info "virt-viewer not found. Attempting to install..."

    if command -v apt &>/dev/null; then
        sudo apt-get install -y virt-viewer
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
# Step 4 — Choose install location
# ---------------------------------------------------------------------------

choose_install_dir() {
    echo ""
    echo "  Where would you like to install pxkit?"
    echo "  Press Enter to accept the default."
    echo ""
    read -r -p "  Install location [$DEFAULT_INSTALL_DIR]: " install_dir
    install_dir="${install_dir:-$DEFAULT_INSTALL_DIR}"

    # Expand tilde if present
    install_dir="${install_dir/#\~/$HOME}"

    # Use global — avoids stdout capture bug when called with $(...)
    INSTALL_DIR="$install_dir"
}

# ---------------------------------------------------------------------------
# Step 5 — Check for existing installation
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
# Step 6 — Download pxkit
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
# Step 7 — Create venv and install dependencies
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
# Step 8 — Symlink to ~/.local/bin
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
# Step 9 — Autostart
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
# Step 10 — Print keyring setup instructions
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Step 11 — Copy and configure default config
# ---------------------------------------------------------------------------

setup_config() {
    local install_dir="$1"
    local config_dir="$HOME/.config/pxkit"
    local config_file="$config_dir/pxkit.yaml"
    local default_config="$install_dir/src/pxkit/data/pxkit.yaml"

    mkdir -p "$config_dir"

    if [[ -f "$config_file" ]]; then
        warn "Config file already exists at $config_file — leaving it alone."
        warn "Skipping Proxmox configuration prompts."
        return
    fi

    cp "$default_config" "$config_file"
    ok "Default config copied to $config_file."

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Configure Proxmox connection"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Enter your Proxmox details below."
    echo "  Press Enter to keep the current default shown in [brackets]."
    echo ""

    # Host
    read -r -p "  Proxmox host [localhost]: " px_host
    px_host="${px_host:-localhost}"

    # Port
    read -r -p "  Proxmox port [8006]: " px_port
    px_port="${px_port:-8006}"

    # Node
    read -r -p "  Proxmox node name [wcyjl1]: " px_node
    px_node="${px_node:-wcyjl1}"

    # Token ID — stored in global so setup_keyring can use it
    read -r -p "  API token ID [carolyn@pam!pxkit]: " px_token_id
    px_token_id="${px_token_id:-carolyn@pam!pxkit}"
    TOKEN_ID="$px_token_id"

    # Write values into the config file using sed
    sed -i "s|host: localhost|host: $px_host|" "$config_file"
    sed -i "s|port: 8006|port: $px_port|" "$config_file"
    sed -i "s|node: wcyjl1|node: $px_node|" "$config_file"
    sed -i "s|token_id: carolyn@pam!pxkit|token_id: $px_token_id|" "$config_file"

    echo ""
    ok "Config written to $config_file."
    info "VM list is pre-populated with examples — edit the file to match your VMs:"
    info "  \$EDITOR $config_file"
}

# ---------------------------------------------------------------------------
# Step 12 — Store API token secret in keyring
# ---------------------------------------------------------------------------

setup_keyring() {
    local install_dir="$1"
    local token_id="$2"
    local venv_python="$install_dir/venv/bin/python3"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Store API token secret"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Enter the secret for your Proxmox API token."
    echo "  It will be stored in your system keyring — not written to disk."
    echo "  Input is hidden."
    echo ""
    read -r -s -p "  API token secret: " px_secret
    echo ""

    if [[ -z "$px_secret" ]]; then
        warn "No secret entered — skipping keyring setup."
        warn "Run this later to store it:"
        warn "  $venv_python -c \"import keyring; keyring.set_password('pxkit', 'TOKEN_ID', 'TOKEN_SECRET')\""
        return
    fi

    PXKIT_TOKEN_ID="$token_id" PXKIT_SECRET="$px_secret" \
    "$venv_python" - << 'PYEOF'
import keyring
import os
import sys
token_id = os.environ['PXKIT_TOKEN_ID']
secret   = os.environ['PXKIT_SECRET']
try:
    keyring.set_password('pxkit', token_id, secret)
    # Verify it was stored correctly
    check = keyring.get_password('pxkit', token_id)
    if check == secret:
        print("  [ ok ]  Secret stored and verified in keyring.")
    else:
        print("  [warn]  Secret stored but verification failed.", file=sys.stderr)
except Exception as e:
    print(f"  [warn]  Keyring store failed: {e}", file=sys.stderr)
    print(f"  [warn]  Store it manually later.", file=sys.stderr)
PYEOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    print_header

    # Find Python
    find_python

    # Install system dependencies
    install_system_deps

    # Install virt-viewer if needed
    install_virt_viewer

    # Choose install location
    choose_install_dir

    # Check for existing install
    check_existing "$INSTALL_DIR"

    # Download
    download_pxkit "$INSTALL_DIR"

    # Venv + dependencies
    setup_venv "$INSTALL_DIR" "$PYTHON"

    # Symlink
    setup_symlink "$INSTALL_DIR"

    # Autostart
    setup_autostart "$INSTALL_DIR/venv/bin/pxkit"

    # Copy and configure default config (sets global TOKEN_ID)
    TOKEN_ID="carolyn@pam!pxkit"
    setup_config "$INSTALL_DIR"

    # Store API token secret in keyring
    setup_keyring "$INSTALL_DIR" "$TOKEN_ID"

    echo ""
    ok "Installation complete. Run: pxkit"
    echo ""
}

main "$@"
