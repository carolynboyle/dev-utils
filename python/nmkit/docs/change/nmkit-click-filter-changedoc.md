# nmkit — Card selection event filter and grid refresh fix

## ui.py

**Path:** `src/nmkit/ui.py`

---

### Change 1 — Replace mousePressEvent with event filters on labels

**Why:** `QFrame.mousePressEvent` is not reliably called when child
widgets cover the frame surface. Clicking the icon or name label was
doing nothing because those widgets absorbed the event first. The fix
is to install `_ClickFilter` event filters directly on the icon and
name labels so clicks on those widgets trigger card selection.
`mousePressEvent` and `mouseDoubleClickEvent` overrides on the card
are removed entirely.

**BEFORE:**
```python
class ConnectionCard(QFrame):
    def _build(self) -> None:
        ...
        icon_label = QLabel()
        ...
        layout.addWidget(icon_label)

        name_label = QLabel(...)
        ...
        layout.addWidget(name_label)

        btn = QPushButton("Connect")
        btn.clicked.connect(self._on_connect)
        btn.pressed.connect(lambda: self._on_select(self))
        layout.addWidget(btn)

    def mousePressEvent(self, event) -> None:
        self._on_select(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_connect()
        super().mouseDoubleClickEvent(event)
```

**AFTER:**
```python
class _ClickFilter(QObject):
    """Event filter that calls a callback on mouse press or double-click."""

    def __init__(self, on_press, on_double_click=None, parent=None):
        super().__init__(parent)
        self._on_press        = on_press
        self._on_double_click = on_double_click

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            self._on_press()
            return False
        if event.type() == QEvent.Type.MouseButtonDblClick:
            if self._on_double_click:
                self._on_double_click()
            return False
        return super().eventFilter(obj, event)


class ConnectionCard(QFrame):
    def _build(self) -> None:
        ...
        icon_label = QLabel()
        icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        ...
        self._install_filter(icon_label)
        layout.addWidget(icon_label)

        name_label = QLabel(...)
        name_label.setCursor(Qt.CursorShape.PointingHandCursor)
        ...
        self._install_filter(name_label)
        layout.addWidget(name_label)

        btn = QPushButton("Connect")
        btn.clicked.connect(self._on_connect)
        btn.pressed.connect(lambda: self._on_select(self))
        layout.addWidget(btn)

    def _install_filter(self, widget: QLabel) -> None:
        filt = _ClickFilter(
            on_press=lambda: self._on_select(self),
            on_double_click=self._on_connect,
            parent=self,
        )
        widget.installEventFilter(filt)
        self._filters.append(filt)
```

---

### Change 2 — Fix post-delete card grid going dead

**Why:** `deleteLater()` removes widgets asynchronously. New cards
added to the grid before the old ones were fully destroyed caused
event routing confusion. Calling `setParent(None)` first removes the
widget from the hierarchy synchronously before scheduling destruction.

**BEFORE:**
```python
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
```

**AFTER:**
```python
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
```

---

### Change 3 — Add QEvent and QObject imports

**Why:** Required by the new `_ClickFilter` class.

**BEFORE:**
```python
from PySide6.QtCore import Qt
```

**AFTER:**
```python
from PySide6.QtCore import Qt, QEvent, QObject
```
