# nmkit — UI restructure and connection dialog rewrite

## Summary

Complete restructure of the main window UI and connection dialog.
Cards no longer have individual Connect buttons. Selection drives
a single Connect button in the toolbar. Description field added
throughout.

---

## connection_dialog.py

**Path:** `src/nmkit/connection_dialog.py`

**Why:** Dropped Qt Designer dependency (`connEdit_ui.py`) entirely.
Dialog is now pure PySide6 code, which is more maintainable, easier
to extend, and eliminates the pylint-ignore workaround for generated
code. Added `description` field (QTextEdit) and `read_only` parameter
for View Details mode.

Key changes:
- No longer imports or uses `Ui_Dialog` from `connEdit_ui.py`
- Builds layout in `_build()` using standard PySide6 widgets
- `read_only=True` makes all fields non-editable and shows Close
  button instead of OK/Cancel
- `get_connection()` now includes `description` key
- Description field has no border/background in read-only mode

---

## ui.py

**Path:** `src/nmkit/ui.py`

**Why:** Cards no longer have individual Connect buttons — single
click selects, double click connects, right click shows context menu.
Toolbar has Add/Edit/Delete/Connect in one row. Selection display
shows connection name and description above the toolbar.

Key changes:
- `ConnectionCard` — icon + name only, no button. Full surface
  clickable via `_ClickFilter` event filters on both labels.
- `_ClickFilter` — extended to handle right-click, passing global
  position to the context menu handler.
- `LauncherUI` — new selection display area (name QLineEdit +
  description QLabel). Toolbar Connect button added alongside
  Add/Edit/Delete. Connect pushed to right with `addStretch()`.
- `_show_card_context_menu()` — right-click menu with Connect,
  separator, View Details, Edit, Delete.
- `_on_view_details()` — opens `ConnectionDialog` in read-only mode.
- `_update_selection_display()` — updates name and description
  fields on card select/deselect.
- `QAction` imported from `PySide6.QtGui` for context menu actions.

---

## connections.yaml

**Path:** `src/nmkit/data/connections.yaml`

**Why:** Added optional `description` field to example entries.
Existing connections without this field continue to work — config
validation passes unknown keys through.

**BEFORE:**
```yaml
connections:
  - name: Example Debian
    host: 192.168.1.100
    port: 22
    user: your-username
    os: debian
```

**AFTER:**
```yaml
connections:
  - name: Example Debian
    host: 192.168.1.100
    port: 22
    user: your-username
    os: debian
    description: ""
```
