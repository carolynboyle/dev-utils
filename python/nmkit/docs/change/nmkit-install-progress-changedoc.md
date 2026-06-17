# nmkit install.sh — progress messaging improvements

## install.sh

**Path:** `install.sh`

---

### Change 1 — Add progress output to git clone

**Why:** The `git clone` step could appear hung with no output since
`2>/dev/null` suppressed all git progress messages.

**BEFORE:**
```bash
download_nmkit() {
    info "Downloading nmkit..."

    if ! command -v git &>/dev/null; then
        die "git is required for installation. Install git and re-run."
    fi

    mkdir -p "$INSTALL_DIR"
    git clone \
        --no-checkout \
        --depth=1 \
        --filter=blob:none \
        "$REPO_URL" \
        "$INSTALL_DIR/repo" 2>/dev/null

    cd "$INSTALL_DIR/repo"
    git sparse-checkout set "$PACKAGE_SUBDIR"
    git checkout 2>/dev/null

    cp -r "$INSTALL_DIR/repo/$PACKAGE_SUBDIR/." "$INSTALL_DIR/"
    rm -rf "$INSTALL_DIR/repo"
    cd "$INSTALL_DIR"

    ok "nmkit downloaded to $INSTALL_DIR."
}
```

**AFTER:**
```bash
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
```

**Changes:**
- Removed `2>/dev/null` suppression so git progress is visible
- Added `--progress` flag to git clone for explicit progress output
- Split into labelled sub-steps with `info` messages
- Removed misleading `info "Downloading nmkit..."` before the git check

---

### Change 2 — Add progress output to pip install

**Why:** `pip install --quiet` produced no output, making the dependency
installation step appear hung on slow connections or machines.

**BEFORE:**
```bash
    info "Installing nmkit and dependencies..."
    "$INSTALL_DIR/venv/bin/pip" install --quiet -e "$INSTALL_DIR"
    ok "Dependencies installed."
```

**AFTER:**
```bash
    info "Installing nmkit and dependencies (this may take a moment)..."
    "$INSTALL_DIR/venv/bin/pip" install --progress-bar on -e "$INSTALL_DIR"
    ok "Dependencies installed."
```

**Changes:**
- Replaced `--quiet` with `--progress-bar on` so pip shows download progress
- Updated info message to set user expectation about duration
