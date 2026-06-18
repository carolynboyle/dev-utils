"""
nmkit.connection_dialog - Add/Edit/View connection dialog for nmkit.

Fully coded in PySide6 — no Qt Designer dependency. Supports three
modes: add (empty form), edit (pre-populated, fields editable), and
view (pre-populated, all fields read-only, Close button only).

Usage:
    from nmkit.connection_dialog import ConnectionDialog

    # Add mode
    dialog = ConnectionDialog(parent=self._window)
    if dialog.exec():
        connection = dialog.get_connection()

    # Edit mode
    dialog = ConnectionDialog(connection=existing, parent=self._window)
    if dialog.exec():
        connection = dialog.get_connection()

    # View Details mode
    dialog = ConnectionDialog(connection=existing, read_only=True,
                              parent=self._window)
    dialog.exec()
"""

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from nmkit.icons import os_hints

log = logging.getLogger("nmkit")

_DEFAULT_PORT = "22"
_DEFAULT_OS   = "unknown"


class ConnectionDialog(QDialog):  # pylint: disable=too-few-public-methods
    """
    Dialog for adding, editing, or viewing a connection.

    Add mode:     All fields empty. OK disabled until name, host, user
                  are filled.
    Edit mode:    Fields pre-populated and editable. OK enabled
                  immediately, re-validates on change.
    View mode:    All fields pre-populated and read-only. Only a Close
                  button is shown.

    Args:
        connection: Existing connection dict to pre-populate.
                    None or omitted for add mode.
        read_only:  True for view-only mode. Ignored if connection
                    is None.
        parent:     Parent widget for dialog positioning.
    """

    def __init__(
        self,
        connection: dict | None = None,
        read_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._connection = connection or {}
        self._read_only  = read_only and connection is not None
        self._edit_mode  = connection is not None and not self._read_only

        self._name_edit   = None
        self._host_edit   = None
        self._port_edit   = None
        self._user_edit   = None
        self._os_combo    = None
        self._desc_edit   = None
        self._ok_button   = None

        self._build()
        self._populate()

        if not self._read_only:
            self._connect_signals()
            self._update_ok_button()

    # -- Public interface -----------------------------------------------------

    def get_connection(self) -> dict:
        """
        Return the connection dict from the current field values.

        Should be called after exec() returns QDialog.Accepted.
        Not meaningful in read-only mode.

        Returns:
            Dict with keys: name, host, port, user, os, description.
        """
        port_text = self._port_edit.text().strip()
        return {
            "name":        self._name_edit.text().strip(),
            "host":        self._host_edit.text().strip(),
            "port":        int(port_text) if port_text.isdigit() else int(_DEFAULT_PORT),
            "user":        self._user_edit.text().strip(),
            "os":          self._os_combo.currentText(),
            "description": self._desc_edit.toPlainText().strip(),
        }

    # -- Build ----------------------------------------------------------------

    def _build(self) -> None:
        """Construct the dialog layout."""
        if self._read_only:
            title = "Connection Details"
        elif self._edit_mode:
            title = "Edit Connection"
        else:
            title = "Add Connection"

        self.setWindowTitle(title)
        self.setMinimumWidth(380)

        outer = QVBoxLayout(self)
        outer.setSpacing(8)
        outer.setContentsMargins(12, 12, 12, 12)

        # -- Connection name (prominent, above form) --------------------------
        name_label = QLabel("<b>Connection Name</b>")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Rocky Linux")
        self._name_edit.setReadOnly(self._read_only)
        outer.addWidget(name_label)
        outer.addWidget(self._name_edit)

        # -- Details form -----------------------------------------------------
        form = QFormLayout()
        form.setSpacing(6)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("hostname or IP")
        self._host_edit.setReadOnly(self._read_only)

        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText(_DEFAULT_PORT)
        self._port_edit.setReadOnly(self._read_only)

        self._os_combo = QComboBox()
        for hint in os_hints():
            self._os_combo.addItem(hint)
        self._os_combo.setEnabled(not self._read_only)

        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("username")
        self._user_edit.setReadOnly(self._read_only)

        form.addRow("Host:", self._host_edit)
        form.addRow("Port:", self._port_edit)
        form.addRow("OS:",   self._os_combo)
        form.addRow("User:", self._user_edit)
        outer.addLayout(form)

        # -- Description ------------------------------------------------------
        desc_label = QLabel("Description:")
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlaceholderText("Optional notes about this connection")
        self._desc_edit.setReadOnly(self._read_only)
        self._desc_edit.setMaximumHeight(80)
        if self._read_only:
            self._desc_edit.setStyleSheet(
                "QTextEdit { border: none; background: transparent; }"
            )
        outer.addWidget(desc_label)
        outer.addWidget(self._desc_edit)

        # -- Buttons ----------------------------------------------------------
        if self._read_only:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)  # pylint: disable=no-member
        else:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
            buttons.accepted.connect(self.accept)  # pylint: disable=no-member
            buttons.rejected.connect(self.reject)  # pylint: disable=no-member

        outer.addWidget(buttons)

    # -- Population -----------------------------------------------------------

    def _populate(self) -> None:
        """Pre-populate fields from the connection dict."""
        if not self._connection:
            return

        self._name_edit.setText(self._connection.get("name", ""))
        self._host_edit.setText(self._connection.get("host", ""))
        self._port_edit.setText(str(self._connection.get("port", _DEFAULT_PORT)))
        self._user_edit.setText(self._connection.get("user", ""))
        self._desc_edit.setPlainText(self._connection.get("description", ""))

        os_hint = self._connection.get("os", _DEFAULT_OS)
        idx     = self._os_combo.findText(os_hint)
        if idx >= 0:
            self._os_combo.setCurrentIndex(idx)

    # -- Validation -----------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connect field change signals to the OK button validator."""
        self._name_edit.textChanged.connect(self._update_ok_button)  # pylint: disable=no-member
        self._host_edit.textChanged.connect(self._update_ok_button)  # pylint: disable=no-member
        self._user_edit.textChanged.connect(self._update_ok_button)  # pylint: disable=no-member

    def _update_ok_button(self) -> None:
        """Enable OK only when name, host, and user have content."""
        if not self._ok_button:
            return
        name_ok = bool(self._name_edit.text().strip())
        host_ok = bool(self._host_edit.text().strip())
        user_ok = bool(self._user_edit.text().strip())
        self._ok_button.setEnabled(name_ok and host_ok and user_ok)
