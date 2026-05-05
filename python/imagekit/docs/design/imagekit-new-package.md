# imagekit — New Package

**Location:** `python/imagekit/` in the `dev-utils` repo

---

## Files to Create

---

### `python/imagekit/pyproject.toml`

**BEFORE:** *(new file)*

**AFTER:**
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

# Install from this directory:
#   cd ~/projects/dev-utils/python/imagekit
#   pip install -e .
#
# Or from anywhere:
#   pip install -e ~/projects/dev-utils/python/imagekit

[project]
name = "imagekit"
version = "0.1.0"
description = "Image utility toolkit for dev-utils / Project Crew"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[project.scripts]
imagekit = "imagekit.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["imagekit*"]

[tool.setuptools.package-data]
imagekit = ["data/*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Why:** Matches the setupkit src-layout pattern. `package-data` entry ensures the `data/` YAML ships with the package when installed.

---

### `python/imagekit/src/imagekit/data/imagekit.yaml`

**BEFORE:** *(new file)*

**AFTER:**
```yaml
# imagekit default configuration

encode:
  default_format: data_uri   # options: data_uri, raw

mime_types:
  png:  "image/png"
  jpg:  "image/jpeg"
  jpeg: "image/jpeg"
  gif:  "image/gif"
  webp: "image/webp"
  svg:  "image/svg+xml"
  bmp:  "image/bmp"
  ico:  "image/x-icon"
```

**Why:** No hard-coded config per project rules. Mime type mappings and output format default live here, not in Python code. Easy to extend when new encode options are added.

---

### `python/imagekit/src/imagekit/__init__.py`

**BEFORE:** *(new file)*

**AFTER:**
```python
"""imagekit — image utility toolkit."""

from imagekit.encode import ImageEncoder

__all__ = ["ImageEncoder"]
```

**Why:** Clean public API. Consumers can `from imagekit import ImageEncoder` without knowing the internal module structure.

---

### `python/imagekit/src/imagekit/encode.py`

**BEFORE:** *(new file)*

**AFTER:**
```python
"""ImageEncoder — base64 encoding operations for image files."""

import base64
from pathlib import Path

import yaml


class ImageEncoder:
    """Encodes image files to base64 or data URI format.

    Usage:
        encoder = ImageEncoder()
        result = encoder.encode("signature.png")
        result = encoder.encode("signature.png", output_format="raw")
    """

    def __init__(self, config: dict | None = None):
        if config is None:
            config_path = Path(__file__).parent / "data" / "imagekit.yaml"
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        self._config = config
        self._mime_types = config.get("mime_types", {})
        self._default_format = config.get("encode", {}).get("default_format", "data_uri")

    def encode(self, image_path: str | Path, output_format: str | None = None) -> str:
        """Encode an image file to base64.

        Args:
            image_path: Path to the image file.
            output_format: 'data_uri' for full data URI string,
                           'raw' for base64 string only.
                           Defaults to value in imagekit.yaml.

        Returns:
            Encoded string in the requested format.

        Raises:
            FileNotFoundError: If the image file does not exist.
            ValueError: If the file extension is not a recognised image type.
        """
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        ext = path.suffix.lstrip(".").lower()
        mime_type = self._mime_types.get(ext)
        if mime_type is None:
            raise ValueError(
                f"Unrecognised image type: .{ext}. "
                f"Supported types: {', '.join(self._mime_types)}"
            )

        raw = base64.b64encode(path.read_bytes()).decode("utf-8")
        fmt = output_format or self._default_format

        if fmt == "raw":
            return raw
        return f"data:{mime_type};base64,{raw}"
```

**Why:** OOP per project rules. Config loaded from `data/imagekit.yaml`, not hard-coded. Explicit `encoding='utf-8'` on file open. Output format is a parameter with a config-driven default, making it easy to add a `--format` CLI flag later without changing the class.

---

### `python/imagekit/src/imagekit/cli.py`

**BEFORE:** *(new file)*

**AFTER:**
```python
"""imagekit CLI entry point."""

import argparse
import sys
from pathlib import Path

from imagekit.encode import ImageEncoder


def cmd_encode(args: argparse.Namespace) -> int:
    """Handle the encode subcommand."""
    encoder = ImageEncoder()
    try:
        result = encoder.encode(args.image, output_format=args.format)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(result)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="imagekit",
        description="Image utility toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # encode subcommand
    enc = subparsers.add_parser("encode", help="Encode an image to base64")
    enc.add_argument("image", help="Path to the image file")
    enc.add_argument(
        "-o", "--output",
        help="Write output to this file instead of stdout",
        default=None
    )
    enc.add_argument(
        "--format",
        choices=["data_uri", "raw"],
        default=None,
        help="Output format: data_uri (default) or raw base64"
    )
    enc.set_defaults(func=cmd_encode)

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
```

**Why:** Subcommand structure (`imagekit encode ...`) leaves room for `imagekit convert ...`, `imagekit resize ...` etc. without breaking existing usage. `--format` flag is wired up now even though the default covers today's use case — costs nothing and avoids a future breaking change.

---

### `python/imagekit/tests/test_encode.py`

**BEFORE:** *(new file)*

**AFTER:**
```python
"""Tests for ImageEncoder."""

import base64
from pathlib import Path

import pytest

from imagekit.encode import ImageEncoder


@pytest.fixture
def encoder():
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

**Why:** Tests cover the four meaningful cases: happy path data URI, raw format, missing file, unsupported type, and file output round-trip. Uses a real minimal PNG binary so there's no external fixture dependency.

---

### `python/imagekit/README.md`

**BEFORE:** *(new file)*

**AFTER:**
```markdown
# imagekit

Image utility toolkit for dev-utils / Project Crew.

## Installation

```bash
cd ~/projects/dev-utils/python/imagekit
pip install -e .
```

## Usage

### CLI

```bash
# Encode to stdout (full data URI)
imagekit encode signature.png

# Encode to file
imagekit encode signature.png -o signature.b64

# Raw base64 only (no data URI prefix)
imagekit encode signature.png --format raw
```

### As a module

```python
from imagekit import ImageEncoder

encoder = ImageEncoder()

# Returns: data:image/png;base64,....
result = encoder.encode("signature.png")

# Returns raw base64 string
result = encoder.encode("signature.png", output_format="raw")
```

## Supported formats

png, jpg/jpeg, gif, webp, svg, bmp, ico

## Extending

Add mime types in `src/imagekit/data/imagekit.yaml`.  
Add new operations (resize, convert) as sibling modules to `encode.py` and register subcommands in `cli.py`.
```

---

## Directory Summary

```
python/imagekit/
  src/
    imagekit/
      __init__.py
      encode.py
      cli.py
      data/
        imagekit.yaml
  tests/
    test_encode.py
  pyproject.toml
  README.md
```

## Dependencies

- stdlib only: `base64`, `pathlib`, `argparse`, `sys`
- `pyyaml>=6.0` (for config loading — already present across the repo)
