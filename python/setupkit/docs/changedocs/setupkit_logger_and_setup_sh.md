# Change Document: setupkit Logger + Revised setup.sh

**Date:** 2026-04-23  
**Affects:** `python/setupkit`, dev-utils repo root  
**Reason:** Logging was embedded inside `installer.py`, making it impossible
to reuse across other setupkit modules without importing the installer.
Extracting it to `logger.py` follows the single-responsibility principle,
matches the pattern used in contactkit and other crew tools, and sets up
a clean template for eventual extraction into a shared dev-utils logging
utility. The `setup.sh` script is also revised to download setupkit from
GitHub into a temp directory rather than using `git+` URLs, which are
unreliable with editable installs and require git to be installed.

---
<!-- 
## File 1: `python/setupkit/src/setupkit/logger.py` (new file)

```python
"""
setupkit.logger - Logging configuration for setupkit.

Provides a single setup_logger() function that configures the setupkit
logger with a rotating file handler and a stderr console handler.

Log location is read from ConfigManager (which reads setupkit.yaml and
the user's dev-utils config.yaml). This keeps log paths consistent with
the rest of the setupkit configuration rather than hardcoding them.

Usage:
    from setupkit.logger import setup_logger

    setup_logger()
    log = logging.getLogger("setupkit")
    log.info("Ready.")

The logger is named 'setupkit' throughout. Other setupkit modules use:
    import logging
    log = logging.getLogger("setupkit")

setup_logger() should be called once, at CLI entry point (main()).
It should NOT be called at module import time.
"""

import logging
import logging.handlers
from pathlib import Path

from setupkit.config import ConfigManager


# Log file size and backup count for rotation.
# 1MB per file, keep 3 backups = max 4MB of logs retained.
_MAX_BYTES    = 1_000_000
_BACKUP_COUNT = 3


def setup_logger(log_dir: Path | None = None) -> None:
    """
    Configure the setupkit logger.

    Sets up two handlers:
      - RotatingFileHandler: writes INFO+ to <log_dir>/setupkit.log
      - StreamHandler:       writes WARNING+ to stderr (visible on problems)

    DEBUG messages go to the file only. The console stays quiet unless
    something goes wrong.

    Args:
        log_dir: Override log directory. Defaults to ConfigManager().log_dir.
                 Useful for testing.

    Returns:
        None. Callers retrieve the logger via logging.getLogger("setupkit").
    """
    if log_dir is None:
        config  = ConfigManager()
        log_dir = config.log_dir

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "setupkit.log"

    logger = logging.getLogger("setupkit")
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if setup_logger() is called more
    # than once (e.g. in tests).
    if logger.handlers:
        return

    # -- File handler (rotating) -------------------------------------------
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # -- Console handler (stderr) ------------------------------------------
    sh = logging.StreamHandler()   # defaults to sys.stderr
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)
```

---

## File 2: `python/setupkit/src/setupkit/installer.py`

### BEFORE — `_setup_logging()` function (remove entirely)

```python
def _setup_logging() -> None:
    """
    Configure the setupkit logger with a file handler and stderr handler.

    File handler writes INFO+ to ~/.local/share/dev-utils/setupkit.log.
    Stderr handler writes WARNING+ to the terminal.
    """
    _config.log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("setupkit")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)
```

### AFTER — remove `_setup_logging()` and update imports in `main()`

Remove `_setup_logging()` from `installer.py` entirely.

In `main()`, replace the call to `_setup_logging()`:

**BEFORE:**
```python
def main() -> None:
    ...
    _setup_logging()
    ...
```

**AFTER:**
```python
def main() -> None:
    ...
    from setupkit.logger import setup_logger
    setup_logger()
    ...
```

Also remove `LOG_PATH` from the module-level config block since it is
no longer used in this file:

**BEFORE:**
```python
_config    = ConfigManager()
CONFIG_DIR = _config.config_dir
LOG_PATH   = _config.log_path
```

**AFTER:**
```python
_config    = ConfigManager()
CONFIG_DIR = _config.config_dir
```

### Why

`_setup_logging()` was a private function inside `installer.py`, making
it impossible for other setupkit modules (future: `initialize.py`,
`manifest.py`) to set up logging without importing the installer.
Moving it to `logger.py` gives every module access to logging setup
via a clean single import. It also fixes the log location — the old
function used `LOG_PATH` from `ConfigManager.log_path`, which pointed
to `~/.local/share/dev-utils/setupkit.log`. The new logger uses
`ConfigManager.log_dir` directly, which is the correct configured path.
`RotatingFileHandler` replaces `FileHandler` to prevent unbounded log
growth. Console output correctly uses `sys.stderr` (unchanged).

---

## File 3: `setup.sh` (revised at dev-utils repo root)

### Why revised

The previous version used `git+https://` URLs to install setupkit via pip.
This approach has two problems:

1. `pip install -e` (editable) does not work with `git+` URLs — pip
   silently ignores the `-e` flag and installs non-editable.
2. It requires `git` to be installed and authenticated.

The revised version downloads the repo as a zip from GitHub (requires
only `curl` and `unzip`, present on virtually all Linux systems), extracts
setupkit to `/tmp/`, installs from the local copy, and leaves the temp
files in place for reference until the next reboot.

### AFTER (full revised script)

```bash
#!/usr/bin/env bash
# setup.sh - Bootstrap script for the dev-utils / Project Crew ecosystem.
#
# Run this once on a new machine before using setupkit.
# After this script completes, use setupkit to install and update tools:
#
#   setupkit init <plugin>    — configure a plugin (run once per plugin)
#   setupkit install          — install all configured plugins
#
# This script is idempotent — safe to run more than once.
# It skips steps that are already complete.
#
# Temp files are left in /tmp/ for reference and will be cleared on reboot.
#
# Requirements: curl, unzip, python3 (3.11+)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# Must match setupkit.yaml venv_path default.
# Override here if your machine uses a different venv location.
# ---------------------------------------------------------------------------

VENV_PATH="/opt/venvs/tools"
REPO_URL="https://github.com/carolynboyle/dev-utils"
BRANCH="main"
SETUPKIT_SUBDIR="python/setupkit"
TMP_DIR="/tmp/dev-utils-bootstrap"
BASHRC="${HOME}/.bashrc"

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
        error "Cannot find Python at '${PYTHON}'. Install Python 3.11+ and re-run."
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
# Step 2: Check for required tools
# ---------------------------------------------------------------------------

for tool in curl unzip; do
    if ! command -v "$tool" &>/dev/null; then
        error "'${tool}' is required but not installed. Install it and re-run."
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Step 3: Create venv if it doesn't exist
# ---------------------------------------------------------------------------

if [[ -d "${VENV_PATH}" ]]; then
    info "Venv already exists at ${VENV_PATH} — skipping creation."
else
    info "Creating venv at ${VENV_PATH}..."
    sudo mkdir -p "${VENV_PATH}"
    sudo "$PYTHON" -m venv "${VENV_PATH}"
fi

# ---------------------------------------------------------------------------
# Step 4: Own the venv
# Prevents root-owned .egg-info files appearing in project directories
# when pip is run with sudo.
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
# Step 5: Download dev-utils repo zip to /tmp/
# ---------------------------------------------------------------------------

ZIP_URL="${REPO_URL}/archive/refs/heads/${BRANCH}.zip"
ZIP_FILE="${TMP_DIR}/dev-utils.zip"

mkdir -p "${TMP_DIR}"

if [[ -f "${ZIP_FILE}" ]]; then
    info "Zip already downloaded at ${ZIP_FILE} — skipping download."
else
    info "Downloading dev-utils from ${ZIP_URL}..."
    curl -L "${ZIP_URL}" -o "${ZIP_FILE}"
fi

# ---------------------------------------------------------------------------
# Step 6: Extract setupkit from zip
# ---------------------------------------------------------------------------

EXTRACT_DIR="${TMP_DIR}/dev-utils-${BRANCH}"
SETUPKIT_DIR="${EXTRACT_DIR}/${SETUPKIT_SUBDIR}"

if [[ -d "${SETUPKIT_DIR}" ]]; then
    info "setupkit already extracted at ${SETUPKIT_DIR} — skipping extraction."
else
    info "Extracting setupkit..."
    unzip -q "${ZIP_FILE}" "dev-utils-${BRANCH}/${SETUPKIT_SUBDIR}/*" -d "${TMP_DIR}"
fi

# ---------------------------------------------------------------------------
# Step 7: Install setupkit into the venv
# ---------------------------------------------------------------------------

PIP="${VENV_PATH}/bin/pip"
SETUPKIT_BIN="${VENV_PATH}/bin/setupkit"

if [[ -f "${SETUPKIT_BIN}" ]]; then
    if "${SETUPKIT_BIN}" --help &>/dev/null; then
        info "setupkit already installed and working — skipping."
    else
        info "setupkit script found but broken — reinstalling..."
        "${PIP}" install "${SETUPKIT_DIR}"
    fi
else
    info "Installing setupkit from ${SETUPKIT_DIR}..."
    "${PIP}" install "${SETUPKIT_DIR}"
fi

# ---------------------------------------------------------------------------
# Step 8: Add venv bin to PATH in ~/.bashrc
# ---------------------------------------------------------------------------

PATH_LINE="export PATH=\"${VENV_PATH}/bin:\$PATH\""

if grep -qF "${VENV_PATH}/bin" "${BASHRC}" 2>/dev/null; then
    info "${VENV_PATH}/bin already in ${BASHRC} — skipping."
else
    info "Adding ${VENV_PATH}/bin to PATH in ${BASHRC}..."
    {
        echo ""
        echo "# Added by dev-utils setup.sh"
        echo "${PATH_LINE}"
    } >> "${BASHRC}"
    info "PATH updated. Run 'source ~/.bashrc' or open a new terminal."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "Bootstrap complete."
echo ""
echo "Temp files left in ${TMP_DIR} for reference (cleared on reboot)."
echo ""
echo "Next steps:"
echo "  1. source ~/.bashrc"
echo "  2. setupkit init <plugin>   — run once per plugin to configure it"
echo "  3. setupkit install         — install all configured plugins"
echo ""
echo "Available plugins: dbkit, viewkit, fletcher, menukit"
echo ""
```

---

## Summary of changes

| File | Change type |
|------|-------------|
| `python/setupkit/src/setupkit/logger.py` | New file |
| `python/setupkit/src/setupkit/installer.py` | Remove `_setup_logging()`, update `main()`, remove `LOG_PATH` |
| `setup.sh` | Revised — zip download instead of `git+` URL |

---

## Testing

```bash
# Verify logger works independently of installer
python3 -c "
from setupkit.logger import setup_logger
import logging
setup_logger()
log = logging.getLogger('setupkit')
log.info('logger test')
print('OK')
"

# Verify log file was created
ls -la ~/.local/share/dev-utils/setupkit.log

# Verify installer still works
setupkit check dbkit

# Test setup.sh idempotency (run twice, should skip all steps)
bash setup.sh
bash setup.sh -->
```
