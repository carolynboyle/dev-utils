# nmkit pylint fixes

## pyproject.toml

**Path:** `pyproject.toml`

**Why:** PySide6 E0611 false positives flood the output. Suppressing
`no-name-in-module` globally for PySide6 imports via pylint config is
cleaner than per-line disables throughout the codebase.

**BEFORE:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**AFTER:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.pylint.master]
extension-pkg-allow-list = ["PySide6"]

[tool.pylint."messages control"]
disable = ["no-name-in-module"]
```

---

## icons.py

**Path:** `src/nmkit/icons.py`

### Change 1 — Move QRect import to top level

**Why:** `C0415 import-outside-toplevel` and `E0611 no-name-in-module`
on the local import inside `_render_tray`. Moving it to the top-level
import block fixes both. The comment justifying the local import
("keep top-level clean") is not a valid reason once we have the
PySide6 pylint suppression in place.

**BEFORE:**
```python
from PySide6.QtCore import Qt
from PySide6.QtGui import (
```

**AFTER:**
```python
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
```

And remove the local import line inside `_render_tray`:

**BEFORE:**
```python
def _render_tray(size: int) -> QPixmap:
    ...
    from PySide6.QtCore import QRect  # local import to keep top-level clean

    pixmap = QPixmap(size, size)
```

**AFTER:**
```python
def _render_tray(size: int) -> QPixmap:
    ...
    pixmap = QPixmap(size, size)
```

### Change 2 — Remove bare re-raise in load_fonts()

**Why:** `W0706 try-except-raise` — catching an exception only to
immediately re-raise it adds no value. Remove the try/except entirely
and let NmkitAssetError propagate naturally.

**BEFORE:**
```python
def load_fonts() -> None:
    ...
    try:
        font_paths = fonts()
    except NmkitAssetError:
        raise

    for style, path in font_paths.items():
```

**AFTER:**
```python
def load_fonts() -> None:
    ...
    font_paths = fonts()

    for style, path in font_paths.items():
```

---

## ui.py

**Path:** `src/nmkit/ui.py`

### Change 1 — Remove unused imports

**Why:** `W0611 unused-import` on `QSize` and `QHBoxLayout`.

**BEFORE:**
```python
from PySide6.QtCore import Qt, QSize
...
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
```

**AFTER:**
```python
from PySide6.QtCore import Qt
...
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
```

### Change 2 — Suppress too-few-public-methods on ConnectionCard

**Why:** `R0903 too-few-public-methods` — ConnectionCard intentionally
exposes only Qt event handlers as its public interface. The class has
more internal behaviour than pylint can see through Qt's signal/slot
mechanism. Inline disable is appropriate here.

**BEFORE:**
```python
class ConnectionCard(QFrame):
    """
    A single connection card showing an OS-hint icon and the host name.
```

**AFTER:**
```python
class ConnectionCard(QFrame):  # pylint: disable=too-few-public-methods
    """
    A single connection card showing an OS-hint icon and the host name.
```

### Change 3 — Suppress too-few-public-methods on LauncherUI

**Why:** Same rationale — `run()` is the single intentional public
method; all other public surface is Qt event callbacks.

**BEFORE:**
```python
class LauncherUI:
    """
    nmkit main window and system tray.
```

**AFTER:**
```python
class LauncherUI:  # pylint: disable=too-few-public-methods
    """
    nmkit main window and system tray.
```

---

## launcher.py

**Path:** `src/nmkit/launcher.py`

### Change 1 — Use with statement for Popen

**Why:** `R1732 consider-using-with` on `subprocess.Popen`. Since
nmkit intentionally detaches nxclient (start_new_session=True) and
does not manage its lifecycle, we can't use a context manager. Inline
disable is the correct fix.

**BEFORE:**
```python
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
```

**AFTER:**
```python
        try:
            subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
```

### Change 2 — Suppress too-few-public-methods on Launcher

**Why:** `R0903 too-few-public-methods` — `launch()` is the single
intentional public method by design. The class has private helpers
that pylint doesn't count toward the threshold.

**BEFORE:**
```python
class Launcher:
    """
    Generates temporary .nxs session files and launches nxclient.
```

**AFTER:**
```python
class Launcher:  # pylint: disable=too-few-public-methods
    """
    Generates temporary .nxs session files and launches nxclient.
```
