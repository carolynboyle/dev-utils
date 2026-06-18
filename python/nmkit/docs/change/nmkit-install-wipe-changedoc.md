# nmkit install.sh — --wipe flag

## install.sh

**Path:** `install.sh`

**Why:** Reinstalling after config or binary path changes required
manually deleting `~/.config/nmkit/` or answering the overwrite
prompt. A `--wipe` flag skips the prompt and removes only the install
directory, preserving `~/.config/nmkit/` and any user-configured
connections.

### Change 1 — Add --wipe to usage comment

**BEFORE:**
```bash
# Usage:
#   bash install.sh
```

**AFTER:**
```bash
# Usage:
#   bash install.sh           — normal install
#   bash install.sh --wipe    — wipe install dir and reinstall (preserves ~/.config/nmkit/)
```

### Change 2 — Add WIPE global

**BEFORE:**
```bash
PYTHON=""
INSTALL_DIR=""
```

**AFTER:**
```bash
PYTHON=""
INSTALL_DIR=""
WIPE=false
```

### Change 3 — Update check_existing() to respect WIPE

**BEFORE:**
```bash
check_existing() {
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "An existing installation was found at $INSTALL_DIR."
        if ! prompt_yn "This will overwrite the existing installation. Continue?" "n"; then
            echo ""
            info "Installation cancelled."
            exit 0
        fi
        info "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    fi
}
```

**AFTER:**
```bash
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
```

### Change 4 — Parse --wipe flag in main()

**BEFORE:**
```bash
main() {
    print_header
    find_python
    ...
}
```

**AFTER:**
```bash
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
    find_python
    ...
}
```
