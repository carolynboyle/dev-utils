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

    PYTHON=""
    local best_minor=0

    for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local minor
            minor=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
            local major
            major=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)

            if [[ "$major" -eq 3 && "$minor" -ge "$MIN_PYTHON_MINOR" && "$minor" -gt "$best_minor" ]]; then
                PYTHON="$candidate"
                best_minor="$minor"
            fi
        fi
    done

    if [[ -z "$PYTHON" ]]; then
        die "Python 3.$MIN_PYTHON_MINOR or newer is required but was not found. Install it and re-run."
    fi

    local version
    version=$("$PYTHON" --version 2>&1)
    ok "Found $version ($PYTHON)"
}

# ---------------------------------------------------------------------------
# Step 2 — Install git
# ---------------------------------------------------------------------------

install_git() {
    if command -v git &>/dev/null; then
        ok "git already installed."
        return
    fi

    info "git not found. Attempting to install..."

    if command -v apt &>/dev/null; then
        sudo apt install -y git
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y git
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm git
    else
        die "Could not detect package manager. Install git manually and re-run."
    fi

    ok "git installed."
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
# Step 4 — Choose install location
# ---------------------------------------------------------------------------

choose_install_dir() {
    echo ""
    echo "  Where would you like to install pxkit?"
    echo "  Press Enter to accept the default."
    echo ""
    read -r -p "  Install location [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

    # Expand tilde if present
    INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"

    echo ""
    info "Installing to: $INSTALL_DIR"
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

    # Sparse checkout — only pull python/pxkit, not the whole monorepo
    mkdir -p "$install_dir"
    git clone \
        --no-checkout \
        --depth=1 \
        --filter=blob:none \
        --sparse \
        "$REPO_URL" \
        "$install_dir/repo"

    cd "$install_dir/repo"
    git sparse-checkout set "$PACKAGE_SUBDIR"
    git checkout main

    # Move package contents up and clean up repo scaffolding
    cp -r "$install_dir/repo/$PACKAGE_SUBDIR/." "$install_dir/"
    rm -rf "$install_dir/repo"
    cd "$install_dir"

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
# Step 9 — XFCE autostart
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
# Step 11 — Print config instructions
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    print_header

    # Find Python (sets global PYTHON)
    PYTHON=""
    find_python

    # Install git if needed
    install_git

    # Install virt-viewer if needed
    install_virt_viewer

    # Choose install location (sets global INSTALL_DIR)
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
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

    # Done — print next steps
    print_keyring_instructions "$INSTALL_DIR"
    print_config_instructions "$INSTALL_DIR"

    ok "Installation complete."
    echo ""
}

main "$@"
