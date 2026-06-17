"""
nmkit.connection_dialog - Add/Edit connection dialog for nmkit.

Wraps the Qt Designer generated Ui_Dialog from connEdit_ui.py.
Handles OS combo population, OK button validation, pre-population
for edit mode, and returns a connection dict on accept.

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
"""

import logging

from PySide6.QtWidgets import QDialog

from nmkit.connEdit_ui import Ui_Dialog
from nmkit.icons import os_hints

log = logging.getLogger("nmkit")

# Default values applied when fields are left empty.
_DEFAULT_PORT = "22"
_DEFAULT_OS   = "unknown"


class ConnectionDialog(QDialog):  # pylint: disable=too-few-public-methods
    """
    Dialog for adding or editing a connection.

    In add mode, all fields are empty and OK is disabled until
    name, host, and user are filled. In edit mode, fields are
    pre-populated and OK is enabled immediately.

    Args:
        connection: Existing connection dict to pre-populate (edit mode).
                    Pass None or omit for add mode.
        parent:     Parent widget for dialog positioning.
    """

    def __init__(self, connection: dict | None = None, parent=None):
        super().__init__(parent)
        self._ui         = Ui_Dialog()
        self._ui.setupUi(self)
        self._edit_mode  = connection is not None
        self._original   = connection or {}

        self.setWindowTitle("Edit Connection" if self._edit_mode else "Add Connection")

        self._populate_os_combo()
        self._connect_signals()

        if self._edit_mode:
            self._prepopulate(connection)
        else:
            self._update_ok_button()

    # -- Public interface -----------------------------------------------------

    def get_connection(self) -> dict:
        """
        Return the connection dict from the current field values.

        Should be called after exec() returns QDialog.Accepted.

        Returns:
            Dict with keys: name, host, port, user, os.
        """
        port_text = self._ui.portLineEdit.text().strip()
        return {
            "name": self._ui.lE_connName.text().strip(),
            "host": self._ui.hostLineEdit.text().strip(),
            "port": int(port_text) if port_text.isdigit() else int(_DEFAULT_PORT),
            "user": self._ui.userLineEdit.text().strip(),
            "os":   self._ui.oSComboBox.currentText(),
        }

    # -- Internal -------------------------------------------------------------

    def _populate_os_combo(self) -> None:
        """Populate the OS combo box from the icons os_hints registry."""
        self._ui.oSComboBox.clear()
        for hint in os_hints():
            self._ui.oSComboBox.addItem(hint)

        # Default selection
        idx = self._ui.oSComboBox.findText(_DEFAULT_OS)
        if idx >= 0:
            self._ui.oSComboBox.setCurrentIndex(idx)

    def _prepopulate(self, connection: dict) -> None:
        """
        Pre-populate all fields from an existing connection dict.

        Args:
            connection: Connection dict with keys: name, host, port,
                        user, os.
        """
        self._ui.lE_connName.setText(connection.get("name", ""))
        self._ui.hostLineEdit.setText(connection.get("host", ""))
        self._ui.portLineEdit.setText(str(connection.get("port", _DEFAULT_PORT)))
        self._ui.userLineEdit.setText(connection.get("user", ""))

        os_hint = connection.get("os", _DEFAULT_OS)
        idx     = self._ui.oSComboBox.findText(os_hint)
        if idx >= 0:
            self._ui.oSComboBox.setCurrentIndex(idx)

        self._update_ok_button()

    def _connect_signals(self) -> None:
        """Connect field change signals to the OK button validator."""
        self._ui.lE_connName.textChanged.connect(self._update_ok_button)   # pylint: disable=no-member
        self._ui.hostLineEdit.textChanged.connect(self._update_ok_button)  # pylint: disable=no-member
        self._ui.userLineEdit.textChanged.connect(self._update_ok_button)  # pylint: disable=no-member

    def _update_ok_button(self) -> None:
        """
        Enable the OK button only when required fields have content.

        Required: name, host, user. Port and OS have defaults.
        """
        name_ok = bool(self._ui.lE_connName.text().strip())
        host_ok = bool(self._ui.hostLineEdit.text().strip())
        user_ok = bool(self._ui.userLineEdit.text().strip())

        ok_button = self._ui.buttonBox.button(
            self._ui.buttonBox.StandardButton.Ok
        )
        if ok_button:
            ok_button.setEnabled(name_ok and host_ok and user_ok)
