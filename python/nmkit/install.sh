#!/usr/bin/env bash
# install.sh — nmkit installer
#
# Usage:
#   bash install.sh           — normal install
#   bash install.sh --wipe    — wipe install dir and reinstall (preserves ~/.config/nmkit/)
#
# Or via curl:
#   curl -sSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/python/nmkit/install.sh | bash
#
# Installs nmkit to a directory of your choice, creates a venv, installs
# dependencies, optionally sets up autostart, and symlinks the nmkit
# command to ~/.local/bin/.
#
# Detects the current OS at install time and writes a flat platform.yaml
# to ~/.config/nmkit/ with values for the detected platform only. If
# nmkit is moved to a different platform, re-run the installer.
#
# Safe to re-run — prompts before overwriting an existing installation.
# Use --wipe to skip the overwrite prompt and force a clean reinstall.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_URL="https://github.com/carolynboyle/dev-utils.git"
PACKAGE_SUBDIR="python/nmkit"
DEFAULT_INSTALL_DIR="$HOME/.local/share/nmkit"
SYMLINK_DIR="$HOME/.local/bin"
SYMLINK_PATH="$SYMLINK_DIR/nmkit"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/nmkit.desktop"
CONFIG_DIR="$HOME/.config/nmkit"
MIN_PYTHON_MINOR=11

# Global — set by find_python, detect_platform, and choose_install_dir.
PYTHON=""
PLATFORM=""
INSTALL_DIR=""
WIPE=false

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  nmkit installer"
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
# Step 1 — Detect OS
# ---------------------------------------------------------------------------

detect_platform() {
    info "Detecting platform..."

    case "$(uname -s)" in
        Linux*)             PLATFORM="linux" ;;
        Darwin*)            PLATFORM="darwin" ;;
        MINGW*|CYGWIN*|MSYS*) PLATFORM="windows" ;;
        *)
            die "Unsupported platform: $(uname -s). nmkit supports Linux, macOS, and Windows."
            ;;
    esac

    ok "Detected platform: $PLATFORM"
}

# ---------------------------------------------------------------------------
# Step 2 — Find Python 3.11+
# ---------------------------------------------------------------------------

find_python() {
    info "Looking for Python 3.11+..."

    local best_python=""
    local best_minor=0

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
    PYTHON="$best_python"
}

# ---------------------------------------------------------------------------
# Step 3 — Check for nxplayer
# ---------------------------------------------------------------------------

check_nxplayer() {
    if command -v nxplayer &>/dev/null || [[ -x "/usr/NX/bin/nxplayer" ]]; then
        ok "NoMachine nxplayer found."
        return
    fi

    warn "NoMachine nxplayer was not found at /usr/NX/bin/nxplayer."
    warn "nmkit requires NoMachine to be installed on this machine."
    warn "Download it from: https://www.nomachine.com/download"
}

# ---------------------------------------------------------------------------
# Step 4 — Choose install location
# ---------------------------------------------------------------------------

choose_install_dir() {
    echo ""
    echo "  Where would you like to install nmkit?"
    echo "  Press Enter to accept the default."
    echo ""
    read -r -p "  Install location [$DEFAULT_INSTALL_DIR]: " install_dir
    install_dir="${install_dir:-$DEFAULT_INSTALL_DIR}"
    install_dir="${install_dir/#\~/$HOME}"
    INSTALL_DIR="$install_dir"
}

# ---------------------------------------------------------------------------
# Step 5 — Check for existing installation
# ---------------------------------------------------------------------------

check_existing() {
    if [[ -d "$INSTALL_DIR" ]]; then
        if [[ "$WIPE" == "true" ]]; then
            info "Wiping existing installation at $INSTALL_DIR..."
            rm -rf "$INSTALL_DIR"
            ok "Existing installation removed."
        else
            warn "An existing installation was found at $INSTALL_DIR."
            if ! prompt_yn "This will overwrite the existing installation. Continue?" "n"; then
                echo ""
                info "Installation cancelled."
                exit 0
            fi
            info "Removing existing installation..."
            rm -rf "$INSTALL_DIR"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 6 — Download nmkit
# ---------------------------------------------------------------------------

download_nmkit() {
    if ! command -v git &>/dev/null; then
        die "git is required for installation. Install git and re-run."
    fi

    mkdir -p "$INSTALL_DIR"

    info "Cloning repository (this may take a moment)..."
    git clone \
        --no-checkout \
        --depth=1 \
        --filter=blob:none \
        --progress \
        "$REPO_URL" \
        "$INSTALL_DIR/repo"

    info "Checking out nmkit files..."
    cd "$INSTALL_DIR/repo"
    git sparse-checkout set "$PACKAGE_SUBDIR"
    git checkout

    info "Copying files to install directory..."
    cp -r "$INSTALL_DIR/repo/$PACKAGE_SUBDIR/." "$INSTALL_DIR/"
    rm -rf "$INSTALL_DIR/repo"
    cd "$INSTALL_DIR"

    ok "nmkit downloaded to $INSTALL_DIR."
}

# ---------------------------------------------------------------------------
# Step 7 — Create venv and install dependencies
# ---------------------------------------------------------------------------

setup_venv() {
    info "Creating virtual environment..."
    "$PYTHON" -m venv "$INSTALL_DIR/venv"
    ok "Virtual environment created."

    info "Installing nmkit and dependencies (this may take a moment)..."
    "$INSTALL_DIR/venv/bin/pip" install --progress-bar on -e "$INSTALL_DIR"
    ok "Dependencies installed."
}

# ---------------------------------------------------------------------------
# Step 8 — Copy default config files
# ---------------------------------------------------------------------------

setup_config() {
    local data_dir="$INSTALL_DIR/src/nmkit/data"

    mkdir -p "$CONFIG_DIR"

    # platform.yaml is always regenerated — it is installer-generated,
    # not user-edited, and must match the current platform and install.
    if [[ -f "$data_dir/platform.yaml" ]]; then
        info "Generating platform.yaml for $PLATFORM..."
        "$INSTALL_DIR/venv/bin/python" - <<PYEOF
import yaml
from pathlib import Path

data_dir  = Path("$data_dir")
config_dir = Path("$CONFIG_DIR")
platform  = "$PLATFORM"

with open(data_dir / "platform.yaml", encoding="utf-8") as f:
    raw = yaml.safe_load(f).get("platform", {})

flat = {}
for key, value in raw.items():
    if isinstance(value, dict):
        if platform not in value:
            print(f"  [warn]  platform.yaml key '{key}' has no entry for '{platform}' — skipping.")
            continue
        flat[key] = value[platform]
    else:
        flat[key] = value

out = config_dir / "platform.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.dump({"platform": flat}, f, default_flow_style=False)

print(f"  [ ok ]  Wrote platform.yaml for {platform} to {out}")
PYEOF
    else
        warn "Default platform.yaml not found at $data_dir — skipping."
    fi

    # nmkit.yaml and connections.yaml are user-editable — only copy if
    # they do not already exist so reinstalls preserve user changes.
    if [[ -f "$data_dir/nmkit.yaml" && ! -f "$CONFIG_DIR/nmkit.yaml" ]]; then
        cp "$data_dir/nmkit.yaml" "$CONFIG_DIR/nmkit.yaml"
        ok "Copied default nmkit.yaml to $CONFIG_DIR/"
    fi

    if [[ -f "$data_dir/connections.yaml" && ! -f "$CONFIG_DIR/connections.yaml" ]]; then
        cp "$data_dir/connections.yaml" "$CONFIG_DIR/connections.yaml"
        ok "Copied default connections.yaml to $CONFIG_DIR/"
    fi

}

# ---------------------------------------------------------------------------
# Step 9 — Symlink to ~/.local/bin
# ---------------------------------------------------------------------------

setup_symlink() {
    local venv_nmkit="$INSTALL_DIR/venv/bin/nmkit"

    mkdir -p "$SYMLINK_DIR"

    if [[ -L "$SYMLINK_PATH" ]]; then
        info "Removing existing symlink at $SYMLINK_PATH."
        rm "$SYMLINK_PATH"
    elif [[ -e "$SYMLINK_PATH" ]]; then
        warn "$SYMLINK_PATH exists and is not a symlink — leaving it alone."
        warn "Add $INSTALL_DIR/venv/bin to your PATH manually."
        return
    fi

    ln -s "$venv_nmkit" "$SYMLINK_PATH"
    ok "Symlink created: $SYMLINK_PATH → $venv_nmkit"

    if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
        warn "$SYMLINK_DIR is not on your PATH."
        warn "Add this to your ~/.bashrc or ~/.zshrc:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# ---------------------------------------------------------------------------
# Step 10 — Autostart
# ---------------------------------------------------------------------------

setup_autostart() {
    local venv_nmkit="$INSTALL_DIR/venv/bin/nmkit"

    echo ""
    if ! prompt_yn "Set up nmkit to launch automatically on login?" "n"; then
        info "Skipping autostart setup."
        return
    fi

    mkdir -p "$AUTOSTART_DIR"

    cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=nmkit
Exec=$venv_nmkit
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=NoMachine connection launcher
EOF

    ok "Autostart entry created at $AUTOSTART_FILE."
}

# ---------------------------------------------------------------------------
# Step 11 — Print next steps
# ---------------------------------------------------------------------------

print_next_steps() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Configure nmkit"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Edit your connections file to add your hosts:"
    echo ""
    echo "    \$EDITOR $CONFIG_DIR/connections.yaml"
    echo ""
    echo "  Each connection needs: name, host, port, user, os"
    echo "  Supported os values: debian, ubuntu, rocky, rhel, fedora,"
    echo "                       opensuse, arch, windows, macos, unknown"
    echo ""
    echo "  Then run nmkit:"
    echo ""
    echo "    nmkit"
    echo ""
    echo "  Font assets (Font Awesome) will be downloaded on first run"
    echo "  if not already present."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    # Parse flags
    for arg in "$@"; do
        case "$arg" in
            --wipe) WIPE=true ;;
            *) die "Unknown argument: $arg. Usage: bash install.sh [--wipe]" ;;
        esac
    done

    print_header
    [[ "$WIPE" == "true" ]] && info "Wipe mode enabled — existing install dir will be removed."
    detect_platform
    find_python
    check_nxplayer
    choose_install_dir
    check_existing
    download_nmkit
    setup_venv
    setup_config
    setup_symlink
    setup_autostart
    print_next_steps
    ok "Installation complete."
    echo ""
}

main "$@"
