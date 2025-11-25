import json
import pytest
import pathlib
import sys

# Ensure repo root is on sys.path so `import Backend...` works when cwd is Backend/Pytest
repo_root = pathlib.Path(__file__).resolve().parents[2]  # two levels up -> repo root
sys.path.insert(0, str(repo_root))

from Backend.BasemapManager import BasemapManager

@pytest.fixture
def sample_config():
    return {
        "basemaps": [
            {
                "id": "osm_standard",
                "name": "OpenStreetMap",
                "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "OSM attribution"
            },
            {
                "id": "esri_satellite",
                "name": "Esri Satellite",
                "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "attribution": "Esri attribution"
            }
        ]
    }

def test_init_missing_file(tmp_path):
    config_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        BasemapManager(config_path=str(config_path))

def test_init_loads_config(tmp_path, sample_config):
    config_path = tmp_path / "basemaps.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")

    manager = BasemapManager(config_path=str(config_path))

    assert manager.config["basemaps"][0]["id"] == "osm_standard"
    assert len(manager.list_basemaps()) == 2

def test_list_basemaps(tmp_path, sample_config):
    config_path = tmp_path / "basemaps.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")

    manager = BasemapManager(config_path=str(config_path))

    basemaps = manager.list_basemaps()
    assert isinstance(basemaps, list)
    assert basemaps[1]["id"] == "esri_satellite"

def test_get_basemap_existing(tmp_path, sample_config):
    config_path = tmp_path / "basemaps.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")

    manager = BasemapManager(config_path=str(config_path))

    result = manager.get_basemap("osm_standard")
    assert result is not None
    assert result["name"] == "OpenStreetMap"

def test_get_basemap_not_found(tmp_path, sample_config):
    config_path = tmp_path / "basemaps.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")

    manager = BasemapManager(config_path=str(config_path))

    assert manager.get_basemap("does_not_exist") is None
