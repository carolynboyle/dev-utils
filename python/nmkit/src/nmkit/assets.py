"""
nmkit.assets - Asset management for nmkit.

Checks for required Font Awesome font files at startup and offers to
download them if missing. Font files are stored in the nmkit data
directory alongside the shipped YAML configs.

Font Awesome Free is licensed under the SIL Open Font License 1.1,
which permits use in commercial products.

Usage:
    from nmkit.assets import check, fonts

    check()   # call at startup before Qt app is created
    f = fonts()  # returns dict of font-name -> Path, used by icons.py

Font files downloaded from:
    https://github.com/FortAwesome/Font-Awesome (releases)
"""

import logging
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import requests

from nmkit.exceptions import NmkitAssetError

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATA_DIR  = Path(__file__).parent / "data"
_FONTS_DIR = _DATA_DIR / "fonts"

# Font Awesome Free release to download.
_FA_VERSION     = "6.5.2"
_FA_RELEASE_URL = (
    f"https://github.com/FortAwesome/Font-Awesome/releases/download"
    f"/{_FA_VERSION}/fontawesome-free-{_FA_VERSION}-desktop.zip"
)

# Expected font files and their paths inside the release zip.
_FONT_FILES = {
    "solid":   "fa-solid-900.ttf",
    "brands":  "fa-brands-400.ttf",
    "regular": "fa-regular-400.ttf",
}

# Zip-internal path prefix for the .ttf files.
_ZIP_TTF_PREFIX = f"fontawesome-free-{_FA_VERSION}-desktop/otfs/"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def check() -> None:
    """
    Check for required font files and prompt to download if missing.

    Should be called once at startup, before the Qt application is
    created. Prints directly to stdout/stderr since the logger and
    Qt UI are not yet initialised.

    Raises:
        NmkitAssetError: If fonts are missing and the user declines
                         to download them, or if download fails.
    """
    missing = _missing_fonts()

    if not missing:
        log.debug("All font assets present.")
        return

    print("\nnmkit: The following Font Awesome font files are missing:")
    for name in missing:
        print(f"  {_FONT_FILES[name]}")

    print(
        f"\nThese are required for OS hint icons. nmkit will download them\n"
        f"from github.com/FortAwesome/Font-Awesome (release {_FA_VERSION}).\n"
        f"Font Awesome Free is licensed under the SIL Open Font License 1.1."
    )

    try:
        answer = input("Download missing fonts? (y/N) ").strip().lower()
    except EOFError:
        answer = "n"

    if answer != "y":
        raise NmkitAssetError(
            "Required font files are missing. "
            "Re-run nmkit and choose 'y' to download, or place the "
            f"font files manually in:\n  {_FONTS_DIR}"
        )

    _download_fonts(missing)


def fonts() -> dict:
    """
    Return a mapping of font style name to Path for each font file.

    Should be called after check() to ensure files are present.

    Returns:
        Dict with keys 'solid', 'brands', 'regular', each mapping
        to a Path object for the corresponding .ttf file.

    Raises:
        NmkitAssetError: If any font file is missing.
    """
    missing = _missing_fonts()
    if missing:
        raise NmkitAssetError(
            f"Font files missing: {', '.join(missing)}. "
            "Run nmkit to trigger the download prompt."
        )

    return {
        name: _FONTS_DIR / filename
        for name, filename in _FONT_FILES.items()
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _missing_fonts() -> list:
    """
    Return a list of font style names whose .ttf files are absent.

    Returns:
        List of style name strings (subset of 'solid', 'brands',
        'regular'). Empty list if all files are present.
    """
    return [
        name
        for name, filename in _FONT_FILES.items()
        if not (_FONTS_DIR / filename).exists()
    ]


def _download_fonts(missing: list) -> None:
    """
    Download the Font Awesome release zip and extract missing .ttf files.

    Args:
        missing: List of style name strings to extract.

    Raises:
        NmkitAssetError: If the download or extraction fails.
    """
    print(f"\nDownloading Font Awesome {_FA_VERSION}...")

    try:
        response = requests.get(_FA_RELEASE_URL, timeout=30, stream=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NmkitAssetError(
            f"Failed to download Font Awesome: {exc}"
        ) from exc

    total     = int(response.headers.get("content-length", 0))
    received  = 0
    chunks    = []

    for chunk in response.iter_content(chunk_size=65536):
        chunks.append(chunk)
        received += len(chunk)
        if total:
            pct = int(received / total * 100)
            print(f"\r  {pct}% ({received} / {total} bytes)", end="", flush=True)

    print()  # newline after progress

    zip_data = BytesIO(b"".join(chunks))

    _FONTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_data) as zf:
            for name in missing:
                filename    = _FONT_FILES[name]
                zip_path    = _ZIP_TTF_PREFIX + filename
                dest        = _FONTS_DIR / filename

                try:
                    data = zf.read(zip_path)
                except KeyError as exc:
                    raise NmkitAssetError(
                        f"Font file not found in zip: {zip_path}"
                    ) from exc

                dest.write_bytes(data)
                print(f"  Saved: {dest}")
                log.info("Downloaded font asset: %s", dest)

    except zipfile.BadZipFile as exc:
        raise NmkitAssetError(
            f"Downloaded file is not a valid zip archive: {exc}"
        ) from exc

    print("\nFont assets ready.\n")


def version() -> str:
    """
    Return the Font Awesome version string nmkit targets.

    Returns:
        Version string, e.g. '6.5.2'.
    """
    return _FA_VERSION


def font_dir() -> Path:
    """
    Return the path to the fonts directory.

    Returns:
        Path to nmkit/data/fonts/.
    """
    return _FONTS_DIR


if __name__ == "__main__":  # pragma: no cover
    # Allow running directly for manual asset installation:
    #   python -m nmkit.assets
    try:
        check()
        print("Assets OK.")
        sys.exit(0)
    except NmkitAssetError as e:
        print(f"Asset error: {e}", file=sys.stderr)
        sys.exit(1)
