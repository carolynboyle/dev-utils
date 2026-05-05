# imagekit — encode.py: Make load_config Public

**File:** `python/imagekit/src/imagekit/encode.py`

---

### Change: Remove underscore prefix from `_load_config`

**BEFORE:**
```python
    def __init__(self, config: dict | None = None):
        self._config = config if config is not None else self._load_config()
        self._mime_types = self._config.get("mime_types", {})
        self._default_format = self._config.get("encode", {}).get("default_format", "data_uri")

    def _load_config(self) -> dict:
        """Load configuration from the bundled imagekit.yaml data file."""
```

**AFTER:**
```python
    def __init__(self, config: dict | None = None):
        self._config = config if config is not None else self.load_config()
        self._mime_types = self._config.get("mime_types", {})
        self._default_format = self._config.get("encode", {}).get("default_format", "data_uri")

    def load_config(self) -> dict:
        """Load configuration from the bundled imagekit.yaml data file."""
```

**Why:** Makes `load_config()` part of the public API — useful for debugging and inspection. Also resolves Pylint R0903 (too-few-public-methods) since the class now has two public methods: `load_config` and `encode`.

---

## Complete corrected file

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
        self._config = config if config is not None else self.load_config()
        self._mime_types = self._config.get("mime_types", {})
        self._default_format = self._config.get("encode", {}).get("default_format", "data_uri")

    def load_config(self) -> dict:
        """Load configuration from the bundled imagekit.yaml data file."""
        config_path = Path(__file__).parent / "data" / "imagekit.yaml"
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError(f"imagekit.yaml is empty or invalid: {config_path}")
        return config

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
