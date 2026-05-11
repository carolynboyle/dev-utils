# README.md

**Path:** python/imagekit/README.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

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

```
