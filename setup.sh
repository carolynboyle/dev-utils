#!/usr/bin/env bash
# setup.sh - Bootstrap script for the dev-utils / Project Crew ecosystem.
#
# Run this once on a new machine before using setupkit.
# After this script completes, use setupkit to install tools:
#
#   setupkit install dbkit
#   setupkit install treekit
#   setupkit install        # installs all configured plugins
#
# This script is idempotent — safe to run more than once.
# It skips steps that are already complete.
#
# Usage:
#   bash setup.sh                          # uses default venv path /opt/venvs/tools
#   bash setup.sh --venv-path /my/venv     # uses a custom venv path
#
# Requirements: python3, pip, git, curl

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

VENV_PATH="/opt/venvs/tools"
SETUPKIT_REPO="https://github.com/carolynboyle/dev-utils.git"
SETUPKIT_SUBDIR="python/setupkit"
REGISTRY_URL="https://raw.githubusercontent.com/carolynboyle/dev-utils/main/setupkit-registry.yaml"
BASHRC="${HOME}/.bashrc"
DEV_UTILS_CONFIG="${HOME}/.config/dev-utils/config.yaml"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv-path)
            VENV_PATH="$2"
            shift 2
            ;;
        --venv-path=*)
            VENV_PATH="${1#*=}"
            shift
            ;;
        -h|--help)
            echo "Usage: bash setup.sh [--venv-path /path/to/venv]"
            echo ""
            echo "Options:"
            echo "  --venv-path PATH   Venv to install tools into (default: /opt/venvs/tools)"
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown argument: $1" >&2
            echo "Usage: bash setup.sh [--venv-path /path/to/venv]" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()    { echo "[INFO]  $*"; }
warning() { echo "[WARN]  $*"; }
error()   { echo "[ERROR] $*" >&2; }

# ---------------------------------------------------------------------------
# Step 1: Find python3
# ---------------------------------------------------------------------------

info "Checking for python3..."

PYTHON=""

if command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    warning "python3 not found on PATH."
    read -rp "Enter the path or command to use for Python 3 (e.g. /usr/bin/python3.11): " PYTHON
    if ! command -v "$PYTHON" &>/dev/null; then
        error "Cannot find Python at '${PYTHON}'. Install Python 3.11+ and re-run this script."
        exit 1
    fi
fi

PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Using Python ${PYTHON_VERSION} at $(command -v "$PYTHON")"

if [[ "${PYTHON_VERSION}" < "3.11" ]]; then
    error "Python 3.11 or higher is required. Found ${PYTHON_VERSION}."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 2: Create venv if it doesn't exist
# ---------------------------------------------------------------------------

if [[ -d "${VENV_PATH}" ]]; then
    info "Venv already exists at ${VENV_PATH} — skipping creation."
else
    info "Creating venv at ${VENV_PATH}..."
    sudo mkdir -p "${VENV_PATH}"
    sudo "$PYTHON" -m venv "${VENV_PATH}"
fi

# ---------------------------------------------------------------------------
# Step 3: Own the venv (avoid root-owned egg-info files)
# ---------------------------------------------------------------------------

CURRENT_USER="$(whoami)"
VENV_OWNER="$(stat -c '%U' "${VENV_PATH}")"

if [[ "${VENV_OWNER}" != "${CURRENT_USER}" ]]; then
    info "Setting ownership of ${VENV_PATH} to ${CURRENT_USER}..."
    sudo chown -R "${CURRENT_USER}:${CURRENT_USER}" "${VENV_PATH}"
else
    info "Venv already owned by ${CURRENT_USER} — skipping chown."
fi

# ---------------------------------------------------------------------------
# Step 4: Write venv path to config if non-default
# ---------------------------------------------------------------------------

DEFAULT_VENV="/opt/venvs/tools"

if [[ "${VENV_PATH}" != "${DEFAULT_VENV}" ]]; then
    info "Writing venv path override to ${DEV_UTILS_CONFIG}..."
    mkdir -p "$(dirname "${DEV_UTILS_CONFIG}")"

    # Write or update the setupkit.venv_path in config.yaml.
    # If the file already has a setupkit: section, we leave it and append
    # a comment directing the user to update manually — full YAML merging
    # is out of scope for a bash script.
    if grep -q "venv_path:" "${DEV_UTILS_CONFIG}" 2>/dev/null; then
        warning "venv_path already set in ${DEV_UTILS_CONFIG} — skipping."
        warning "Update it manually if needed: venv_path: ${VENV_PATH}"
    else
        cat >> "${DEV_UTILS_CONFIG}" << YAML

# Added by setup.sh
setupkit:
  venv_path: ${VENV_PATH}
YAML
        info "venv_path written to ${DEV_UTILS_CONFIG}."
    fi
fi

# ---------------------------------------------------------------------------
# Step 5: Install setupkit into the venv
# ---------------------------------------------------------------------------

PIP="${VENV_PATH}/bin/pip"
SETUPKIT_BIN="${VENV_PATH}/bin/setupkit"

if [[ -f "${SETUPKIT_BIN}" ]]; then
    if "${SETUPKIT_BIN}" --help &>/dev/null; then
        info "setupkit already installed and working — skipping."
    else
        info "setupkit script found but broken — reinstalling..."
        "${PIP}" install "git+${SETUPKIT_REPO}#subdirectory=${SETUPKIT_SUBDIR}"
    fi
else
    info "Installing setupkit into ${VENV_PATH}..."
    "${PIP}" install "git+${SETUPKIT_REPO}#subdirectory=${SETUPKIT_SUBDIR}"
fi

# ---------------------------------------------------------------------------
# Step 6: Add venv bin to PATH in ~/.bashrc
# ---------------------------------------------------------------------------

PATH_LINE="export PATH=\"${VENV_PATH}/bin:\$PATH\""

if grep -qF "${VENV_PATH}/bin" "${BASHRC}" 2>/dev/null; then
    info "${VENV_PATH}/bin already in ${BASHRC} — skipping."
else
    info "Adding ${VENV_PATH}/bin to PATH in ${BASHRC}..."
    echo "" >> "${BASHRC}"
    echo "# Added by dev-utils setup.sh" >> "${BASHRC}"
    echo "${PATH_LINE}" >> "${BASHRC}"
    info "PATH updated. Run 'source ~/.bashrc' or open a new terminal."
fi

# ---------------------------------------------------------------------------
# Step 7: Run setupkit init for all packages in the registry
# ---------------------------------------------------------------------------

info "Initialising plugin configs from registry..."

SETUPKIT="${VENV_PATH}/bin/setupkit"

if ! command -v curl &>/dev/null; then
    warning "curl not found — skipping automatic plugin init."
    warning "Run 'setupkit init <name>' manually for each plugin."
else
    # Fetch registry and extract package names (simple grep — no yq needed).
    REGISTRY=$(curl -sf "${REGISTRY_URL}") || {
        warning "Could not fetch registry from ${REGISTRY_URL}."
        warning "Run 'setupkit init <name>' manually for each plugin."
        REGISTRY=""
    }

    if [[ -n "${REGISTRY}" ]]; then
        # Extract lines that look like "  name:" (two-space indent = package entry).
        PACKAGES=$(echo "${REGISTRY}" | grep -E '^  [a-z]' | awk -F: '{print $1}' | tr -d ' ')

        for pkg in ${PACKAGES}; do
            config_file="${HOME}/.config/dev-utils/setupkit/${pkg}.yaml"
            if [[ -f "${config_file}" ]]; then
                info "Plugin config already exists for ${pkg} — skipping init."
            else
                info "Initialising ${pkg}..."
                "${SETUPKIT}" init "${pkg}" || warning "setupkit init ${pkg} failed — skipping."
            fi
        done
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo "  1. Run: source ~/.bashrc"
echo "  2. Run: setupkit install      (installs all configured plugins)"
echo "  3. Or:  setupkit install <name>"
echo ""
