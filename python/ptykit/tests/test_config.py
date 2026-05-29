"""
tests/test_config.py

Tests for ptykit.config.ConfigLoader.
"""

import pytest
import yaml
from pathlib import Path
from ptykit.config import ConfigLoader, config_path
from ptykit.exceptions import PtyKitConfigError


@pytest.fixture
def valid_config(tmp_path):
    config = {
        "program": "advent",
        "intercept": ["map", "hint"],
        "plugins": ["ptykit_ccc.map_plugin:MapPlugin"],
    }
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    return path


def test_loads_valid_config(valid_config):
    loader = ConfigLoader("advent", config_file=valid_config)
    assert loader.program == "advent"
    assert loader.intercept == ["map", "hint"]
    assert loader.plugins == ["ptykit_ccc.map_plugin:MapPlugin"]


def test_intercept_normalised_to_lowercase(tmp_path):
    config = {
        "program": "advent",
        "intercept": ["MAP", "Hint"],
        "plugins": [],
    }
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    loader = ConfigLoader("advent", config_file=path)
    assert loader.intercept == ["map", "hint"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(PtyKitConfigError, match="not found"):
        ConfigLoader("advent", config_file=tmp_path / "missing.yaml")


def test_missing_required_field_raises(tmp_path):
    config = {"program": "advent", "intercept": ["map"]}  # missing plugins
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="missing required fields"):
        ConfigLoader("advent", config_file=path)


def test_invalid_yaml_raises(tmp_path):
    path = tmp_path / "advent.yaml"
    path.write_text(":::: not valid yaml ::::", encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="Failed to parse"):
        ConfigLoader("advent", config_file=path)


def test_intercept_not_list_raises(tmp_path):
    config = {"program": "advent", "intercept": "map", "plugins": []}
    path = tmp_path / "advent.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    with pytest.raises(PtyKitConfigError, match="must be a list"):
        ConfigLoader("advent", config_file=path)


def test_config_path_returns_correct_location():
    p = config_path("advent")
    assert p.name == "advent.yaml"
    assert "dev-utils" in str(p)
    assert "ptykit" in str(p)
