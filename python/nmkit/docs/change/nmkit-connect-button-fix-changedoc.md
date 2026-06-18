# nmkit — Connect button and card selection fix

## ui.py

**Path:** `src/nmkit/ui.py`

**Why:** The previous fix added `_on_select(self)` to `_on_connect()`
which caused the Connect button to select the card but broke the
actual connection launch. The root cause is that the Connect button
as a child widget absorbs click events before they reach the card's
`mousePressEvent`. The correct fix is to wire the button's `pressed`
signal to selection separately from the `clicked` signal that triggers
the connection.

### Change 1 — Remove _on_select from _on_connect

**BEFORE:**
```python
    def _on_connect(self) -> None:
        """Handle Connect button click — select card and launch session."""
        self._on_select(self)
        name = self._connection.get("name", "unknown")
```

**AFTER:**
```python
    def _on_connect(self) -> None:
        """Handle Connect button click — launch the NoMachine session."""
        name = self._connection.get("name", "unknown")
```

### Change 2 — Wire pressed signal to card selection

**Why:** `pressed` fires before `clicked`, so the card is selected
before the connection launches. Using a separate signal keeps
selection and launch concerns independent.

**BEFORE:**
```python
        btn = QPushButton("Connect")
        btn.clicked.connect(self._on_connect)  # pylint: disable=no-member
        layout.addWidget(btn)
```

**AFTER:**
```python
        btn = QPushButton("Connect")
        btn.clicked.connect(self._on_connect)           # pylint: disable=no-member
        btn.pressed.connect(lambda: self._on_select(self))  # pylint: disable=no-member
        layout.addWidget(btn)
```
