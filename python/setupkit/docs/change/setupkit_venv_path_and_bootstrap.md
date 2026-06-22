# Change Document: setupkit venv_path + Bootstrap Script

**Date:** 2026-04-23  
**Affects:** `python/setupkit`, dev-utils repo root  
**Reason:** setupkit had no way to know where the tools venv lives, and new
machine setup required manual PATH edits before setupkit could be used.
This change makes the venv location configurable and provides a one-time
bootstrap script that handles everything before setupkit takes over.

---

## File 1: `python/setupkit/src/setupkit/data/setupkit.yaml`

### BEFORE

```yaml
# setupkit.yaml - setupkit default configuration
#
# This file ships with setupkit and provides defaults.
# To override, add a 'setupkit:' section to ~/.config/dev-utils/config.yaml
# with only the keys you want to change.
#
# Example override in ~/.config/dev-utils/config.yaml:
#
#   setupkit:
#     config_dir: ~/my-custom-plugins
#     log_dir: ~/logs/dev-utils

setupkit:
  config_dir: ~/.config/dev-utils/setupkit
  log_dir: ~/.local/share/dev-utils
```

### AFTER

```yaml
# setupkit.yaml - setupkit default configuration
#
# This file ships with setupkit and provides defaults.
# To override, add a 'setupkit:' section to ~/.config/dev-utils/config.yaml
# with only the keys you want to change.
#
# Example override in ~/.config/dev-utils/config.yaml:
#
#   setupkit:
#     config_dir: ~/my-custom-plugins
#     log_dir: ~/logs/dev-utils
#     venv_path: /opt/venvs/tools

setupkit:
  config_dir: ~/.config/dev-utils/setupkit
  log_dir: ~/.local/share/dev-utils
  venv_path: /opt/venvs/tools
```

### Why

`venv_path` tells setupkit (and `setup.sh`) where the shared tools venv
lives. Keeping it in the yaml means it can be overridden per-machine
without changing code. The default `/opt/venvs/tools` matches the existing
installation on all current machines.

---

## File 2: `python/setupkit/src/setupkit/config.py`

### BEFORE (relevant section only — add after `log_path` property)

```python
    @property
    def log_path(self) -> Path:
        """
        Path to the setupkit plain text log file.

        Returns:
            Resolved Path to <log_dir>/setupkit.log.
        """
        return self.log_dir / "setupkit.log"
```

### AFTER

```python
    # @property
    # def log_path(self) -> Path:
    #     """
    #     Path to the setupkit plain text log file.

    #     Returns:
    #         Resolved Path to <log_dir>/setupkit.log.
    #     """
    #     return self.log_dir / "setupkit.log"

    # @property
    # def venv_path(self) -> Path:
    #     """
    #     Path to the shared tools virtual environment.

    #     This is the venv into which all Project Crew tools are installed.
    #     Defaults to /opt/venvs/tools. Override in
    #     ~/.config/dev-utils/config.yaml under the setupkit: section.

    #     Returns:
    #         Resolved Path to the tools venv directory.
    #     """
    #     return Path(self._config.get("venv_path", "/opt/venvs/tools")).expanduser().resolve()
```

### Why

Exposes `venv_path` as a first-class config property consistent with
`config_dir` and `log_dir`. Other setupkit modules can now use
`config.venv_path` instead of hardcoding the path.

---

## File 3: `setup.sh` (new file at dev-utils repo root)

```bash
# #!/usr/bin/env bash
# # setup.sh - Bootstrap script for the dev-utils / Project Crew ecosystem.
# #
# # Run this once on a new machine before using setupkit.
# # After this script completes, use setupkit to install and update tools:
# #
# #   setupkit install dbkit
# #   setupkit install viewkit
# #   setupkit install fletcher
# #   setupkit install menukit
# #
# # This script is idempotent — safe to run more than once.
# # It skips steps that are already complete.
# #
# # Requirements: python3, pip, git, curl

# set -euo pipefail

# # ---------------------------------------------------------------------------
# # Configuration
# # Default venv path — must match setupkit.yaml venv_path default.
# # Override here if your machine uses a different location, or set
# # venv_path in ~/.config/dev-utils/config.yaml after running this script.
# # ---------------------------------------------------------------------------

# VENV_PATH="/opt/venvs/tools"
# SETUPKIT_REPO="https://github.com/carolynboyle/dev-utils.git"
# SETUPKIT_SUBDIR="python/setupkit"
# BASHRC="${HOME}/.bashrc"

# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# info()    { echo "[INFO]  $*"; }
# warning() { echo "[WARN]  $*"; }
# error()   { echo "[ERROR] $*" >&2; }

# # ---------------------------------------------------------------------------
# # Step 1: Find python3
# # ---------------------------------------------------------------------------

# info "Checking for python3..."

# PYTHON=""

# if command -v python3 &>/dev/null; then
#     PYTHON="python3"
# else
#     warning "python3 not found on PATH."
#     read -rp "Enter the path or command to use for Python 3 (e.g. /usr/bin/python3.11): " PYTHON
#     if ! command -v "$PYTHON" &>/dev/null; then
#         error "Cannot find Python at '${PYTHON}'. Install Python 3.11+ and re-run this script."
#         exit 1
#     fi
# fi

# PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
# info "Using Python ${PYTHON_VERSION} at $(command -v "$PYTHON")"

# if [[ "${PYTHON_VERSION}" < "3.11" ]]; then
#     error "Python 3.11 or higher is required. Found ${PYTHON_VERSION}."
#     exit 1
# fi

# # ---------------------------------------------------------------------------
# # Step 2: Create venv if it doesn't exist
# # ---------------------------------------------------------------------------

# if [[ -d "${VENV_PATH}" ]]; then
#     info "Venv already exists at ${VENV_PATH} — skipping creation."
# else
#     info "Creating venv at ${VENV_PATH}..."
#     sudo mkdir -p "${VENV_PATH}"
#     sudo "$PYTHON" -m venv "${VENV_PATH}"
# fi

# # ---------------------------------------------------------------------------
# # Step 3: Own the venv (avoid root-owned egg-info files)
# # ---------------------------------------------------------------------------

# CURRENT_USER="$(whoami)"
# VENV_OWNER="$(stat -c '%U' "${VENV_PATH}")"

# if [[ "${VENV_OWNER}" != "${CURRENT_USER}" ]]; then
#     info "Setting ownership of ${VENV_PATH} to ${CURRENT_USER}..."
#     sudo chown -R "${CURRENT_USER}:${CURRENT_USER}" "${VENV_PATH}"
# else
#     info "Venv already owned by ${CURRENT_USER} — skipping chown."
# fi

# # ---------------------------------------------------------------------------
# # Step 4: Install setupkit into the venv
# # ---------------------------------------------------------------------------

# PIP="${VENV_PATH}/bin/pip"
# SETUPKIT_BIN="${VENV_PATH}/bin/setupkit"

# if [[ -f "${SETUPKIT_BIN}" ]]; then
#     # Verify it actually works — a broken install leaves the script but
#     # not the package
#     if "${SETUPKIT_BIN}" --help &>/dev/null; then
#         info "setupkit already installed and working — skipping."
#     else
#         info "setupkit script found but broken — reinstalling..."
#         "${PIP}" install "git+${SETUPKIT_REPO}#subdirectory=${SETUPKIT_SUBDIR}"
#     fi
# else
#     info "Installing setupkit into ${VENV_PATH}..."
#     "${PIP}" install "git+${SETUPKIT_REPO}#subdirectory=${SETUPKIT_SUBDIR}"
# fi

# # ---------------------------------------------------------------------------
# # Step 5: Add venv bin to PATH in ~/.bashrc
# # ---------------------------------------------------------------------------

# PATH_LINE="export PATH=\"${VENV_PATH}/bin:\$PATH\""

# if grep -qF "${VENV_PATH}/bin" "${BASHRC}" 2>/dev/null; then
#     info "${VENV_PATH}/bin already in ${BASHRC} — skipping."
# else
#     info "Adding ${VENV_PATH}/bin to PATH in ${BASHRC}..."
#     echo "" >> "${BASHRC}"
#     echo "# Added by dev-utils setup.sh" >> "${BASHRC}"
#     echo "${PATH_LINE}" >> "${BASHRC}"
#     info "PATH updated. Run 'source ~/.bashrc' or open a new terminal."
# fi

# # ---------------------------------------------------------------------------
# # Done
# # ---------------------------------------------------------------------------

# echo ""
# echo "Bootstrap complete."
# echo ""
# echo "Next steps:"
# echo "  1. Run: source ~/.bashrc"
# echo "  2. Run: setupkit init <plugin>   for each plugin you want to install"
# echo "  3. Run: setupkit install         to install all configured plugins"
# echo ""
# echo "Available plugins: dbkit, viewkit, fletcher, menukit"
# echo ""
# ```

# ### Why

# A single script that a new contributor runs once to get from zero to a
# working setupkit install. Handles the chicken-and-egg problem of needing
# setupkit to install things before setupkit itself is installed. Idempotent
# — safe to re-run. Installs setupkit directly from GitHub so no local clone
# is required. Adds the tools venv to PATH permanently so `setupkit` works
# from any terminal after that.

# ---

# ## Summary of changes

# | File | Change type |
# |------|-------------|
# | `python/setupkit/src/setupkit/data/setupkit.yaml` | Add `venv_path` key |
# | `python/setupkit/src/setupkit/config.py` | Add `venv_path` property |
# | `setup.sh` | New file at repo root |

# ## Testing

# After applying these changes:

# ```bash
# # On a fresh machine (or in a test environment):
# bash setup.sh
# source ~/.bashrc
# setupkit --help

# # Verify venv_path is readable:
# python3 -c "from setupkit.config import ConfigManager; print(ConfigManager().venv_path)"
```
