# end_session.sh — Chrome Profile Cleanup

**Date:** 2026-07-15  
**File:** `end_session.sh`

---

## Change 1: Add Chrome singleton file cleanup block

### BEFORE
```bash
log "--- Pass 2 complete ---"

# --- End session manager ---
```

### AFTER
```bash
log "--- Pass 2 complete ---"

# --- Chrome profile cleanup ---
log "--- Chrome profile cleanup ---"
for f in SingletonLock SingletonSocket SingletonCookie; do
    path="$HOME/.config/google-chrome/$f"
    if [ -f "$path" ] || [ -L "$path" ]; then
        rm -f "$path"
        log "Removed $path"
    fi
done

# --- End session manager ---
```

### Why
When Chrome is killed by PID in pass 2 rather than closing cleanly, it leaves
`SingletonLock`, `SingletonSocket`, and `SingletonCookie` behind in
`~/.config/google-chrome/`. On next launch Chrome sees these stale files, treats
them as evidence of a running instance, and either refuses to start or requires
manual profile recovery.

This block removes all three files unconditionally after pass 2 completes. The
files are safe to delete — Chrome recreates them on startup. Both regular files
and symlinks are handled (`-f` and `-L` check).
