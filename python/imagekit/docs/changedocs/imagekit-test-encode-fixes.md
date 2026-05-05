# imagekit — test_encode.py Pylint Fixes

**File:** `python/imagekit/tests/test_encode.py`

---

## Changes

### 1. Remove unused `Path` import

**BEFORE:**
```python
import base64
from pathlib import Path

import pytest
```

**AFTER:**
```python
import base64

import pytest
```

**Why:** `Path` is never referenced directly in the test file. `tmp_path` is a pytest built-in fixture that already returns a `Path` object. Pylint correctly flagged this as unused.

---

### 2. Add `pylint: disable=redefined-outer-name` and docstrings

**BEFORE:**
```python
def test_encode_returns_data_uri(encoder, sample_png):
    result = encoder.encode(sample_png)
    assert result.startswith("data:image/png;base64,")


def test_encode_raw_format(encoder, sample_png):
    result = encoder.encode(sample_png, output_format="raw")
    # Should be valid base64 with no data URI prefix
    assert not result.startswith("data:")
    decoded = base64.b64decode(result)
    assert decoded[:8] == b'\x89PNG\r\n\x1a\n'


def test_encode_file_not_found(encoder):
    with pytest.raises(FileNotFoundError):
        encoder.encode("nonexistent.png")


def test_encode_unsupported_type(encoder, tmp_path):
    bad = tmp_path / "file.txt"
    bad.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="Unrecognised image type"):
        encoder.encode(bad)


def test_encode_output_to_file(encoder, sample_png, tmp_path):
    out = tmp_path / "output.txt"
    result = encoder.encode(sample_png)
    out.write_text(result, encoding="utf-8")
    assert out.read_text(encoding="utf-8") == result
```

**AFTER:**
```python
def test_encode_returns_data_uri(encoder, sample_png):  # pylint: disable=redefined-outer-name
    """Encoded output should be a full data URI string."""
    result = encoder.encode(sample_png)
    assert result.startswith("data:image/png;base64,")


def test_encode_raw_format(encoder, sample_png):  # pylint: disable=redefined-outer-name
    """Raw format should return base64 only, with no data URI prefix."""
    result = encoder.encode(sample_png, output_format="raw")
    assert not result.startswith("data:")
    decoded = base64.b64decode(result)
    assert decoded[:8] == b'\x89PNG\r\n\x1a\n'


def test_encode_file_not_found(encoder):  # pylint: disable=redefined-outer-name
    """Missing file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        encoder.encode("nonexistent.png")


def test_encode_unsupported_type(encoder, tmp_path):  # pylint: disable=redefined-outer-name
    """Unsupported file extension should raise ValueError."""
    bad = tmp_path / "file.txt"
    bad.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="Unrecognised image type"):
        encoder.encode(bad)


def test_encode_output_to_file(encoder, sample_png, tmp_path):  # pylint: disable=redefined-outer-name
    """Output written to file should match the encoded result."""
    out = tmp_path / "output.txt"
    result = encoder.encode(sample_png)
    out.write_text(result, encoding="utf-8")
    assert out.read_text(encoding="utf-8") == result
```

**Why:** Pylint W0621 fires on every test function that takes a fixture as a parameter because the parameter name shadows the fixture function defined at module scope. This is standard pytest idiom and the disable comment is the correct fix — it's not suppressing a real problem, it's telling Pylint this pattern is intentional. Docstrings added to satisfy C0116.

---

## Complete corrected file

```python
"""Tests for ImageEncoder."""

import base64

import pytest

from imagekit.encode import ImageEncoder


@pytest.fixture
def encoder():
    """Provide a default ImageEncoder instance."""
    return ImageEncoder()


@pytest.fixture
def sample_png(tmp_path):
    """Create a minimal valid PNG for testing."""
    # 1x1 red pixel PNG (binary literal — no external dependency)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    p = tmp_path / "test.png"
    p.write_bytes(png_bytes)
    return p


def test_encode_returns_data_uri(encoder, sample_png):  # pylint: disable=redefined-outer-name
    """Encoded output should be a full data URI string."""
    result = encoder.encode(sample_png)
    assert result.startswith("data:image/png;base64,")


def test_encode_raw_format(encoder, sample_png):  # pylint: disable=redefined-outer-name
    """Raw format should return base64 only, with no data URI prefix."""
    result = encoder.encode(sample_png, output_format="raw")
    assert not result.startswith("data:")
    decoded = base64.b64decode(result)
    assert decoded[:8] == b'\x89PNG\r\n\x1a\n'


def test_encode_file_not_found(encoder):  # pylint: disable=redefined-outer-name
    """Missing file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        encoder.encode("nonexistent.png")


def test_encode_unsupported_type(encoder, tmp_path):  # pylint: disable=redefined-outer-name
    """Unsupported file extension should raise ValueError."""
    bad = tmp_path / "file.txt"
    bad.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="Unrecognised image type"):
        encoder.encode(bad)


def test_encode_output_to_file(encoder, sample_png, tmp_path):  # pylint: disable=redefined-outer-name
    """Output written to file should match the encoded result."""
    out = tmp_path / "output.txt"
    result = encoder.encode(sample_png)
    out.write_text(result, encoding="utf-8")
    assert out.read_text(encoding="utf-8") == result
```

---

## Remaining item

**`Import "pytest" could not be resolved`** — this is not a code problem. It means pytest is not installed in the active venv. Fix:

```bash
pip install pytest
```

This error will disappear once pytest is installed.
