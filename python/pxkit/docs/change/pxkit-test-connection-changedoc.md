# pxkit — Changedoc: test_connection.py updates

## Summary

Updated `test_connection.py` to match the current `_format_vv(data,
conn_type)` signature and the new behaviors it implements (type injection,
proxy exclusion, ca newline unescaping). Added `test_raises_when_no_keyring_backend`
to `TestGetTokenSecret`. Updated `MOCK_SPICE_DATA` to include the fields
needed to exercise the new behaviors.

---

## tests/test_connection.py

**File:** `tests/test_connection.py`

---

### Change 1: Add `keyring.errors` import

**BEFORE**
```python
from unittest.mock import MagicMock, patch

import pytest

from pxkit.connection import ProxmoxConnection
```

**AFTER**
```python
from unittest.mock import MagicMock, patch

import pytest

import keyring.errors

from pxkit.connection import ProxmoxConnection
```

**Why:** Required for `test_raises_when_no_keyring_backend`, which patches
`keyring.get_password` to raise `keyring.errors.NoKeyringError`.

---

### Change 2: Expand `MOCK_SPICE_DATA`

**BEFORE**
```python
MOCK_SPICE_DATA = {
    "type": "spice",
    "host": "localhost",
    "port": "61000",
    "password": "secret",
    "tls-port": None,
}
```

**AFTER**
```python
MOCK_SPICE_DATA = {
    "host": "localhost",
    "port": "61000",
    "password": "secret",
    "tls-port": None,
    "proxy": "https://localhost:61000",
    "ca": "-----BEGIN CERTIFICATE-----\\nMIIB\\nEND CERTIFICATE-----",
}
```

**Why:** `type` removed — Proxmox does not return it; `_format_vv` now injects
it from `conn_type` arg instead. `proxy` added to verify it gets excluded from
output. `ca` added with escaped `\n` to verify unescaping behavior.

---

### Change 3: Rewrite `TestFormatVv`

**BEFORE**
```python
class TestFormatVv:

    def test_produces_virt_viewer_header(self):
        """Output starts with [virt-viewer] header."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert result.startswith("[virt-viewer]\n")

    def test_includes_non_null_fields(self):
        """Non-null fields are included in output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert "host=localhost" in result
        assert "port=61000" in result
        assert "password=secret" in result

    def test_excludes_null_fields(self):
        """Null fields are excluded from output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert "tls-port" not in result

    def test_ends_with_newline(self):
        """Output ends with a trailing newline."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert result.endswith("\n")
```

**AFTER**
```python
class TestFormatVv:

    def test_produces_virt_viewer_header(self):
        """Output starts with [virt-viewer] header."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert result.startswith("[virt-viewer]\n")

    def test_injects_type_from_conn_type_arg(self):
        """type= line comes from conn_type arg, not from data dict."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert "type=spice" in result

    def test_includes_non_null_fields(self):
        """Non-null fields are included in output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert "host=localhost" in result
        assert "port=61000" in result
        assert "password=secret" in result

    def test_excludes_null_fields(self):
        """Null fields are excluded from output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert "tls-port" not in result

    def test_excludes_proxy_field(self):
        """proxy field is excluded — Proxmox returns its own proxy, not ours."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert "proxy=" not in result

    def test_ca_newlines_unescaped(self):
        """Escaped \\n in ca field is converted to real newlines."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert "\\n" not in result
        assert "\n" in result.split("ca=", 1)[1]

    def test_ends_with_newline(self):
        """Output ends with a trailing newline."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA, "spice")
        assert result.endswith("\n")
```

**Why:** All calls updated to pass `conn_type` as the required second arg.
Three new tests added:
- `test_injects_type_from_conn_type_arg` — verifies `type=spice` appears
  in output even though `MOCK_SPICE_DATA` no longer contains a `type` key
- `test_excludes_proxy_field` — verifies Proxmox's proxy value is dropped
- `test_ca_newlines_unescaped` — verifies `\\n` in ca cert is converted to
  real newlines so remote-viewer can parse the certificate

---

### Change 4: Add `test_raises_when_no_keyring_backend` to `TestGetTokenSecret`

**BEFORE**
```python
class TestGetTokenSecret:

    def test_returns_secret_from_keyring(self, mock_config):
        """Returns token secret when found in keyring."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value="mysecret"):
            result = conn._get_token_secret()
        assert result == "mysecret"

    def test_raises_when_secret_not_found(self, mock_config):
        """Raises PxkitConnectionError when keyring returns None."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value=None):
            with pytest.raises(PxkitConnectionError, match="not found in keyring"):
                conn._get_token_secret()
```

**AFTER**
```python
class TestGetTokenSecret:

    def test_returns_secret_from_keyring(self, mock_config):
        """Returns token secret when found in keyring."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value="mysecret"):
            result = conn._get_token_secret()
        assert result == "mysecret"

    def test_raises_when_secret_not_found(self, mock_config):
        """Raises PxkitConnectionError when keyring returns None."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value=None):
            with pytest.raises(PxkitConnectionError, match="not found in keyring"):
                conn._get_token_secret()

    def test_raises_when_no_keyring_backend(self, mock_config):
        """Raises PxkitConnectionError when no keyring backend is available."""
        conn = ProxmoxConnection(mock_config)
        with patch(
            "pxkit.connection.keyring.get_password",
            side_effect=keyring.errors.NoKeyringError,
        ):
            with pytest.raises(PxkitConnectionError, match="No keyring backend"):
                conn._get_token_secret()
```

**Why:** `NoKeyringError` is raised when kwalletd5 isn't on D-Bus (a known
failure mode on the T490). Without this catch, the exception bypasses the
`PxkitConnectionError` handler in `ui.py` and surfaces as an unhandled
crash. This test is written to drive the corresponding fix needed in
`connection.py` (`_get_token_secret` must catch `NoKeyringError` and
re-raise as `PxkitConnectionError`). The test will fail until that
`connection.py` fix is applied.

---

## ⚠ Pending: connection.py fix required

`test_raises_when_no_keyring_backend` will fail until `_get_token_secret`
in `connection.py` is updated to catch `NoKeyringError`:

```python
import keyring.errors

def _get_token_secret(self) -> str:
    token_id = self._proxmox["token_id"]
    try:
        secret = keyring.get_password(_KEYRING_SERVICE, token_id)
    except keyring.errors.NoKeyringError as exc:
        raise PxkitConnectionError(
            "No keyring backend available. "
            "Is kwalletd5 running and registered on D-Bus?"
        ) from exc

    if secret is None:
        raise PxkitConnectionError(
            f"Token secret for '{token_id}' not found in keyring service "
            f"'{_KEYRING_SERVICE}'."
        )
    return secret
```
