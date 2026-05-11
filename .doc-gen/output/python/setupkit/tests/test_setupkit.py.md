# test_setupkit.py

**Path:** python/setupkit/tests/test_setupkit.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
tests/test_setupkit.py - Tests for setupkit.

Covers plugin config loading, manifest parsing and filtering,
version comparison, and install orchestration.

External HTTP calls are mocked throughout — no network access required.
"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from setupkit.exceptions import (
    InstallError,
    ManifestError,
    PluginConfigError,
    VersionError,
)
from setupkit.installer import (
    InstallResult,
    check_plugin,
    config_path,
    install_plugin,
    list_configured_plugins,
)
from setupkit.manifest import ManifestData, ManifestFile, fetch_manifest, filter_files
from setupkit.plugin import InstallConfig, PluginConfig, load_plugin
from setupkit.version import VersionInfo, get_installed_version, is_update_available, parse_version


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PLUGIN_YAML = textwrap.dedent("""\
    name: dbkit
    version: 0.1.0
    manifest_url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/.doc-gen/manifest.fletch
    pyproject: python/dbkit/pyproject.toml
    path_prefix: python/dbkit/dbkit/
    install:
      method: pip
      url: git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit
""")

VALID_MANIFEST_YAML = textwrap.dedent("""\
    repo: https://github.com/carolynboyle/dev-utils
    branch: master
    url_type: raw
    generated: '2026-04-16 10:00:00'
    version: 0.2.0
    files:
      - path: python/dbkit/pyproject.toml
        url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/dbkit/pyproject.toml
      - path: python/dbkit/dbkit/__init__.py
        url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/dbkit/dbkit/__init__.py
      - path: python/dbkit/dbkit/connection.py
        url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/dbkit/dbkit/connection.py
      - path: python/viewkit/viewkit/__init__.py
        url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/python/viewkit/viewkit/__init__.py
""")


@pytest.fixture
def plugin_yaml(tmp_path) -> Path:
    """Write a valid plugin.yaml to a temp directory and return its path."""
    p = tmp_path / "dbkit.yaml"
    p.write_text(VALID_PLUGIN_YAML, encoding="utf-8")
    return p


@pytest.fixture
def valid_plugin_config() -> PluginConfig:
    """Return a valid PluginConfig instance."""
    return PluginConfig(
        name="dbkit",
        version="0.1.0",
        manifest_url="https://raw.githubusercontent.com/carolynboyle/dev-utils/master/.doc-gen/manifest.fletch",
        pyproject="python/dbkit/pyproject.toml",
        path_prefix="python/dbkit/dbkit/",
        install=InstallConfig(
            method="pip",
            url="git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit",
        ),
    )


@pytest.fixture
def valid_manifest() -> ManifestData:
    """Return a valid ManifestData instance with mixed plugin files."""
    return ManifestData(
        repo="https://github.com/carolynboyle/dev-utils",
        branch="master",
        url_type="raw",
        generated="2026-04-16 10:00:00",
        version="0.2.0",
        files=[
            ManifestFile("python/dbkit/pyproject.toml", "https://raw.../pyproject.toml"),
            ManifestFile("python/dbkit/dbkit/__init__.py", "https://raw.../__init__.py"),
            ManifestFile("python/dbkit/dbkit/connection.py", "https://raw.../connection.py"),
            ManifestFile("python/viewkit/viewkit/__init__.py", "https://raw.../viewkit/__init__.py"),
        ],
    )


# ---------------------------------------------------------------------------
# plugin.py
# ---------------------------------------------------------------------------

class TestLoadPlugin:

    def test_loads_valid_yaml(self, plugin_yaml):
        """A valid plugin.yaml is loaded into a PluginConfig without error."""
        config = load_plugin(plugin_yaml)
        assert config.name == "dbkit"
        assert config.version == "0.1.0"
        assert config.path_prefix == "python/dbkit/dbkit/"
        assert config.install.method == "pip"

    def test_raises_if_file_missing(self, tmp_path):
        """Missing plugin.yaml raises PluginConfigError."""
        with pytest.raises(PluginConfigError, match="not found"):
            load_plugin(tmp_path / "nonexistent.yaml")

    def test_raises_if_missing_required_fields(self, tmp_path):
        """plugin.yaml missing required fields raises PluginConfigError."""
        p = tmp_path / "bad.yaml"
        p.write_text("name: dbkit\n", encoding="utf-8")
        with pytest.raises(PluginConfigError, match="missing required fields"):
            load_plugin(p)

    def test_raises_if_unsupported_install_method(self, tmp_path):
        """Unsupported install method raises PluginConfigError."""
        bad = yaml.dump({
            "name": "dbkit",
            "version": "0.1.0",
            "manifest_url": "https://example.com/manifest.fletch",
            "pyproject": "python/dbkit/pyproject.toml",
            "path_prefix": "python/dbkit/dbkit/",
            "install": {"method": "cargo", "url": "https://example.com"},
        })
        p = tmp_path / "bad.yaml"
        p.write_text(bad, encoding="utf-8")
        with pytest.raises(PluginConfigError, match="unsupported install method"):
            load_plugin(p)

    def test_raises_if_empty_file(self, tmp_path):
        """Empty plugin.yaml raises PluginConfigError."""
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        with pytest.raises(PluginConfigError, match="empty or not a mapping"):
            load_plugin(p)


# ---------------------------------------------------------------------------
# manifest.py
# ---------------------------------------------------------------------------

class TestFetchManifest:

    def test_parses_valid_manifest(self):
        """A valid manifest.fletch response is parsed into ManifestData."""
        mock_response = MagicMock()
        mock_response.text = VALID_MANIFEST_YAML
        mock_response.raise_for_status = MagicMock()

        with patch("setupkit.manifest.requests.get", return_value=mock_response):
            manifest = fetch_manifest("https://example.com/manifest.fletch")

        assert manifest.version == "0.2.0"
        assert manifest.repo == "https://github.com/carolynboyle/dev-utils"
        assert len(manifest.files) == 4

    def test_raises_on_http_error(self):
        """HTTP error raises ManifestError."""
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError()

        with patch("setupkit.manifest.requests.get", return_value=mock_response):
            with pytest.raises(ManifestError, match="HTTP"):
                fetch_manifest("https://example.com/manifest.fletch")

    def test_raises_on_timeout(self):
        """Timeout raises ManifestError."""
        import requests as req
        with patch(
            "setupkit.manifest.requests.get",
            side_effect=req.exceptions.Timeout(),
        ):
            with pytest.raises(ManifestError, match="Timed out"):
                fetch_manifest("https://example.com/manifest.fletch")

    def test_raises_on_missing_fields(self):
        """Manifest missing required fields raises ManifestError."""
        mock_response = MagicMock()
        mock_response.text = "repo: https://github.com/example\n"
        mock_response.raise_for_status = MagicMock()

        with patch("setupkit.manifest.requests.get", return_value=mock_response):
            with pytest.raises(ManifestError, match="missing required fields"):
                fetch_manifest("https://example.com/manifest.fletch")

    def test_version_is_none_when_absent(self):
        """Manifest without version field returns version=None."""
        no_version = VALID_MANIFEST_YAML.replace("version: 0.2.0\n", "")
        mock_response = MagicMock()
        mock_response.text = no_version
        mock_response.raise_for_status = MagicMock()

        with patch("setupkit.manifest.requests.get", return_value=mock_response):
            manifest = fetch_manifest("https://example.com/manifest.fletch")

        assert manifest.version is None


class TestFilterFiles:

    def test_filters_by_prefix(self, valid_manifest):
        """filter_files returns only files matching path_prefix or pyproject."""
        result = filter_files(
            valid_manifest,
            path_prefix="python/dbkit/dbkit/",
            pyproject="python/dbkit/pyproject.toml",
        )
        paths = [f.path for f in result]
        assert "python/dbkit/dbkit/__init__.py" in paths
        assert "python/dbkit/dbkit/connection.py" in paths
        assert "python/dbkit/pyproject.toml" in paths
        assert "python/viewkit/viewkit/__init__.py" not in paths

    def test_includes_pyproject(self, valid_manifest):
        """pyproject path is included even though it doesn't match path_prefix."""
        result = filter_files(
            valid_manifest,
            path_prefix="python/dbkit/dbkit/",
            pyproject="python/dbkit/pyproject.toml",
        )
        assert any(f.path == "python/dbkit/pyproject.toml" for f in result)

    def test_returns_empty_for_unknown_prefix(self, valid_manifest):
        """Unknown prefix with no matching pyproject returns empty list."""
        result = filter_files(
            valid_manifest,
            path_prefix="python/unknownkit/",
            pyproject="python/unknownkit/pyproject.toml",
        )
        assert result == []


# ---------------------------------------------------------------------------
# version.py
# ---------------------------------------------------------------------------

class TestParseVersion:

    def test_parses_valid_version(self):
        """Valid version strings are parsed without error."""
        v = parse_version("1.2.3")
        assert str(v) == "1.2.3"

    def test_raises_on_invalid_version(self):
        """Invalid version string raises VersionError."""
        with pytest.raises(VersionError, match="Could not parse"):
            parse_version("not-a-version")


class TestIsUpdateAvailable:

    def test_update_available_when_upstream_newer(self):
        """Returns update_available=True when upstream is newer."""
        with patch("setupkit.version.get_installed_version", return_value="0.1.0"):
            result = is_update_available("dbkit", "0.2.0")
        assert result.update_available is True

    def test_no_update_when_versions_equal(self):
        """Returns update_available=False when versions match."""
        with patch("setupkit.version.get_installed_version", return_value="0.1.0"):
            result = is_update_available("dbkit", "0.1.0")
        assert result.update_available is False

    def test_not_installed_when_package_absent(self):
        """Returns not_installed=True when package is not installed."""
        with patch("setupkit.version.get_installed_version", return_value=None):
            result = is_update_available("dbkit", "0.1.0")
        assert result.not_installed is True
        assert result.update_available is True

    def test_no_update_when_upstream_version_absent(self):
        """Returns update_available=False when manifest has no version."""
        with patch("setupkit.version.get_installed_version", return_value="0.1.0"):
            result = is_update_available("dbkit", None)
        assert result.update_available is False


# ---------------------------------------------------------------------------
# installer.py
# ---------------------------------------------------------------------------

class TestConfigPath:

    def test_returns_correct_path(self):
        """config_path returns the expected path for a plugin name."""
        expected = Path.home() / ".config" / "dev-utils" / "setupkit" / "dbkit.yaml"
        assert config_path("dbkit") == expected


class TestListConfiguredPlugins:

    def test_returns_sorted_plugin_names(self, tmp_path):
        """list_configured_plugins returns sorted plugin names."""
        (tmp_path / "viewkit.yaml").touch()
        (tmp_path / "dbkit.yaml").touch()
        (tmp_path / "menukit.yaml").touch()

        with patch("setupkit.installer.CONFIG_DIR", tmp_path):
            result = list_configured_plugins()

        assert result == ["dbkit", "menukit", "viewkit"]

    def test_returns_empty_when_dir_missing(self, tmp_path):
        """Returns empty list when config directory does not exist."""
        with patch("setupkit.installer.CONFIG_DIR", tmp_path / "nonexistent"):
            result = list_configured_plugins()
        assert result == []


class TestCheckPlugin:

    def test_returns_up_to_date_result(self, tmp_path, valid_plugin_config, valid_manifest):
        """check_plugin returns skipped result when plugin is up to date."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed="0.2.0",
                upstream="0.2.0",
                update_available=False,
                not_installed=False,
            )),
        ):
            result = check_plugin("dbkit")

        assert result.action == "checked"
        assert result.success is True
        assert "up to date" in result.message

    def test_returns_update_available_result(self, valid_plugin_config, valid_manifest):
        """check_plugin reports update available when upstream is newer."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed="0.1.0",
                upstream="0.2.0",
                update_available=True,
                not_installed=False,
            )),
        ):
            result = check_plugin("dbkit")

        assert "update available" in result.message


class TestInstallPlugin:

    def test_skips_when_up_to_date(self, valid_plugin_config, valid_manifest):
        """install_plugin skips when plugin is already up to date."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed="0.2.0",
                upstream="0.2.0",
                update_available=False,
                not_installed=False,
            )),
        ):
            result = install_plugin("dbkit")

        assert result.action == "skipped"
        assert result.success is True

    def test_installs_when_not_installed(self, valid_plugin_config, valid_manifest):
        """install_plugin runs pip when package is not installed."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed=None,
                upstream="0.2.0",
                update_available=True,
                not_installed=True,
            )),
            patch("setupkit.installer._run_pip_install") as mock_pip,
        ):
            result = install_plugin("dbkit")

        mock_pip.assert_called_once_with(valid_plugin_config)
        assert result.action == "installed"
        assert result.success is True

    def test_force_reinstalls_up_to_date_plugin(self, valid_plugin_config, valid_manifest):
        """install_plugin with force=True reinstalls even when up to date."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed="0.2.0",
                upstream="0.2.0",
                update_available=False,
                not_installed=False,
            )),
            patch("setupkit.installer._run_pip_install") as mock_pip,
        ):
            result = install_plugin("dbkit", force=True)

        mock_pip.assert_called_once()
        assert result.action == "updated"

    def test_raises_install_error_on_pip_failure(self, valid_plugin_config, valid_manifest):
        """install_plugin raises InstallError when pip fails."""
        with (
            patch("setupkit.installer.load_plugin", return_value=valid_plugin_config),
            patch("setupkit.installer.fetch_manifest", return_value=valid_manifest),
            patch("setupkit.installer.is_update_available", return_value=VersionInfo(
                package="dbkit",
                installed=None,
                upstream="0.2.0",
                update_available=True,
                not_installed=True,
            )),
            patch(
                "setupkit.installer._run_pip_install",
                side_effect=InstallError("pip failed"),
            ),
        ):
            with pytest.raises(InstallError, match="pip failed"):
                install_plugin("dbkit")

```
