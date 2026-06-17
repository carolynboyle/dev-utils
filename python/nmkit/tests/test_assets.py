"""
tests/test_assets.py - Tests for nmkit.assets.

Covers font file presence detection, download prompt behaviour,
and the fonts() accessor. Filesystem and network calls are mocked
throughout — no actual downloads or font files required.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import zipfile
import io

import pytest

from nmkit.assets import (
    _discover_fonts,
    _FONT_FILES,
    _FONTS_DIR,
    _FA_VERSION,
    check,
    fonts,
    font_dir,
    version,
    _missing_fonts,
    _download_fonts,
)
from nmkit.exceptions import NmkitAssetError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_zip(font_files: dict, prefix: str) -> bytes:
    """
    Build a minimal in-memory zip containing fake FA-style .otf files.

    Uses Font Awesome naming conventions so _discover_fonts() can
    match them by keyword (solid, brands, regular).

    Args:
        font_files: Dict of style -> local filename (subset of _FONT_FILES).
                    Only the style keys are used; zip entries use FA names.
        prefix:     Zip-internal path prefix for the files.

    Returns:
        Raw zip bytes.
    """
    # Map style keys to FA-style zip entry names matching real FA release.
    fa_names = {
        "solid":   "Font Awesome 6 Free-Solid-900.otf",
        "brands":  "Font Awesome 6 Brands-Regular-400.otf",
        "regular": "Font Awesome 6 Free-Regular-400.otf",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for style in font_files:
            zf.writestr(prefix + fa_names[style], b"fake otf content")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# version() and font_dir()
# ---------------------------------------------------------------------------

class TestMetadata:

    def test_version_returns_string(self):
        """version() returns a non-empty string."""
        assert isinstance(version(), str)
        assert version() != ""

    def test_version_matches_module_constant(self):
        """version() matches _FA_VERSION."""
        assert version() == _FA_VERSION

    def test_font_dir_returns_path(self):
        """font_dir() returns a Path."""
        assert isinstance(font_dir(), Path)

    def test_font_dir_ends_with_fonts(self):
        """font_dir() path ends with 'fonts'."""
        assert font_dir().name == "fonts"


# ---------------------------------------------------------------------------
# _missing_fonts()
# ---------------------------------------------------------------------------

class TestMissingFonts:

    def test_all_missing_when_dir_empty(self, tmp_path, monkeypatch):
        """All fonts reported missing when fonts dir is empty."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        missing = _missing_fonts()
        assert set(missing) == set(_FONT_FILES.keys())

    def test_none_missing_when_all_present(self, tmp_path, monkeypatch):
        """No fonts reported missing when all files exist."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        for filename in _FONT_FILES.values():
            (tmp_path / filename).write_bytes(b"fake")
        missing = _missing_fonts()
        assert missing == []

    def test_partial_missing_reported(self, tmp_path, monkeypatch):
        """Only actually missing fonts are reported."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        # Write only the solid font
        solid_filename = _FONT_FILES["solid"]
        (tmp_path / solid_filename).write_bytes(b"fake")
        missing = _missing_fonts()
        assert "solid" not in missing
        assert "brands" in missing
        assert "regular" in missing


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------

class TestCheck:

    def test_no_prompt_when_all_present(self, tmp_path, monkeypatch, capsys):
        """No prompt is shown and no download triggered when fonts are present."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        for filename in _FONT_FILES.values():
            (tmp_path / filename).write_bytes(b"fake")

        check()  # should complete without prompting or raising

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_raises_when_user_declines(self, tmp_path, monkeypatch):
        """Raises NmkitAssetError when user answers 'n' to download prompt."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "n")

        with pytest.raises(NmkitAssetError, match="Required font files are missing"):
            check()

    def test_raises_when_user_presses_enter(self, tmp_path, monkeypatch):
        """Default (Enter) is treated as 'N' — raises NmkitAssetError."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "")

        with pytest.raises(NmkitAssetError):
            check()

    def test_triggers_download_when_user_says_yes(self, tmp_path, monkeypatch):
        """Calls _download_fonts when user answers 'y'."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "y")

        with patch("nmkit.assets._download_fonts") as mock_dl:
            check()

        mock_dl.assert_called_once()

    def test_eof_on_input_treated_as_no(self, tmp_path, monkeypatch):
        """EOFError on input (non-interactive) is treated as 'N'."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        monkeypatch.setattr("builtins.input", MagicMock(side_effect=EOFError))

        with pytest.raises(NmkitAssetError):
            check()


# ---------------------------------------------------------------------------
# fonts()
# ---------------------------------------------------------------------------

class TestFonts:

    def test_returns_dict_of_paths(self, tmp_path, monkeypatch):
        """fonts() returns a dict mapping style names to Path objects."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        for filename in _FONT_FILES.values():
            (tmp_path / filename).write_bytes(b"fake")

        result = fonts()
        assert isinstance(result, dict)
        assert set(result.keys()) == set(_FONT_FILES.keys())
        for path in result.values():
            assert isinstance(path, Path)

    def test_paths_point_to_existing_files(self, tmp_path, monkeypatch):
        """fonts() paths point to files that actually exist."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        for filename in _FONT_FILES.values():
            (tmp_path / filename).write_bytes(b"fake")

        result = fonts()
        for path in result.values():
            assert path.exists()

    def test_raises_when_fonts_missing(self, tmp_path, monkeypatch):
        """fonts() raises NmkitAssetError when any font file is missing."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)

        with pytest.raises(NmkitAssetError, match="Font files missing"):
            fonts()


# ---------------------------------------------------------------------------
# _download_fonts()
# ---------------------------------------------------------------------------

class TestDownloadFonts:

    def test_writes_font_files(self, tmp_path, monkeypatch):
        """Downloaded fonts are written to the fonts directory."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        prefix   = f"fontawesome-free-{_FA_VERSION}-desktop/otfs/"
        zip_data = _make_fake_zip(_FONT_FILES, prefix)

        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(len(zip_data))}
        mock_response.iter_content = lambda chunk_size: [zip_data]
        mock_response.raise_for_status = MagicMock()

        with patch("nmkit.assets.requests.get", return_value=mock_response):
            _download_fonts(list(_FONT_FILES.keys()))

        for filename in _FONT_FILES.values():
            assert (tmp_path / filename).exists()

    def test_raises_on_network_error(self, tmp_path, monkeypatch):
        """Raises NmkitAssetError when the HTTP request fails."""
        import requests as req
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)

        with patch(
            "nmkit.assets.requests.get",
            side_effect=req.RequestException("timeout"),
        ):
            with pytest.raises(NmkitAssetError, match="Failed to download"):
                _download_fonts(list(_FONT_FILES.keys()))

    def test_raises_on_bad_zip(self, tmp_path, monkeypatch):
        """Raises NmkitAssetError when downloaded data is not a valid zip."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)

        mock_response = MagicMock()
        mock_response.headers = {"content-length": "10"}
        mock_response.iter_content = lambda chunk_size: [b"not a zip"]
        mock_response.raise_for_status = MagicMock()

        with patch("nmkit.assets.requests.get", return_value=mock_response):
            with pytest.raises(NmkitAssetError, match="not a valid zip"):
                _download_fonts(list(_FONT_FILES.keys()))

    def test_only_missing_fonts_downloaded(self, tmp_path, monkeypatch):
        """Only the requested (missing) fonts are extracted, not all."""
        monkeypatch.setattr("nmkit.assets._FONTS_DIR", tmp_path)
        prefix   = f"fontawesome-free-{_FA_VERSION}-desktop/otfs/"
        zip_data = _make_fake_zip(_FONT_FILES, prefix)

        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(len(zip_data))}
        mock_response.iter_content = lambda chunk_size: [zip_data]
        mock_response.raise_for_status = MagicMock()

        with patch("nmkit.assets.requests.get", return_value=mock_response):
            # Only download 'solid'
            _download_fonts(["solid"])

        assert (tmp_path / _FONT_FILES["solid"]).exists()
        assert not (tmp_path / _FONT_FILES["brands"]).exists()
        assert not (tmp_path / _FONT_FILES["regular"]).exists()
