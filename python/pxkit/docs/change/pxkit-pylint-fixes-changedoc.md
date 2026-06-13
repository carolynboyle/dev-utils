# pxkit — Changedoc: pylint fixes

## Summary

Five pylint issues resolved to bring the codebase to a clean pass.
No logic changes — formatting, newlines, and suppression comments only.

---

## src/pxkit/config.py

### Change 1 — Add missing final newline (C0304)

**Why:** Pylint requires files to end with a newline. Missing newline
on the last line of the file.

**BEFORE:**
```python
        return result
```
*(no newline after)*

**AFTER:**
```python
        return result
```
*(trailing newline added)*

---

## src/pxkit/exceptions.py

### Change 1 — Add missing final newline (C0304)

**Why:** Same as config.py — file did not end with a newline.

**BEFORE:**
```python
class PxkitLaunchError(PxkitError):
    """Raised when a browser or remote-viewer launch fails."""
```
*(no newline after)*

**AFTER:**
```python
class PxkitLaunchError(PxkitError):
    """Raised when a browser or remote-viewer launch fails."""
```
*(trailing newline added)*

---

## src/pxkit/ui.py

### Change 1 — Split long mouse wheel binding line (C0301)

**Why:** Line 174 was 138 characters — over the 100-char limit. The
nested lambda was extracted into a named inner function for readability
and to bring the binding calls under the line limit.

**BEFORE:**
```python
        # Mouse wheel scrolling.
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(-1 * (ev.delta // 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
```

**AFTER:**
```python
        # Mouse wheel scrolling — bind on enter, unbind on leave so the
        # scroll wheel doesn't get captured when the cursor is elsewhere.
        def _on_mousewheel(ev):
            canvas.yview_scroll(-1 * (ev.delta // 120), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
```

---

### Change 2 — Suppress R0903 on LauncherUI (too-few-public-methods)

**Why:** `LauncherUI` intentionally exposes only `run()` as its public
interface — that is the correct design for a UI class with a single
entry point. The warning is a false positive here.

**BEFORE:**
```python
class LauncherUI:
```

**AFTER:**
```python
class LauncherUI:  # pylint: disable=too-few-public-methods
```

---

## src/pxkit/launcher.py

### Change 1 — Suppress R1732 on subprocess.Popen (consider-using-with)

**Why:** `Popen` is used intentionally without a context manager.
`remote-viewer` is launched as a detached process — we do not wait for
it to exit. Using `with subprocess.Popen(...)` would block until the
process exits, which is the opposite of the intended behaviour.

**BEFORE:**
```python
            subprocess.Popen(
                ["remote-viewer", str(vv_path)],
```

**AFTER:**
```python
            subprocess.Popen(  # pylint: disable=consider-using-with
                ["remote-viewer", str(vv_path)],
```

---

## src/pxkit/connection.py

### Change 1 — Suppress R0903 on ProxmoxConnection (too-few-public-methods)

**Why:** `ProxmoxConnection` intentionally exposes only
`get_spice_ticket()` as its public interface. Additional public methods
will be added when SSH tunnel support is implemented. The warning is
a false positive for the current scope.

**BEFORE:**
```python
class ProxmoxConnection:
```

**AFTER:**
```python
class ProxmoxConnection:  # pylint: disable=too-few-public-methods
```
