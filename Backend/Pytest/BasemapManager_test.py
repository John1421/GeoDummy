import pytest
import json
import os

# Ensure repo root is on sys.path so `import Backend...` works when cwd is Backend/Pytest
repo_root = pathlib.Path(__file__).resolve().parents[2]  # two levels up -> repo root
sys.path.insert(0, str(repo_root))

from Backend.BasemapManager import BasemapManager

# Path to basemaps config
BASEMAPS_PATH = os.path.join("Backend", "basemaps.json")

def load_real_basemaps():
    with open(BASEMAPS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["basemaps"]

def test_init_with_valid_config():
    basemaps = load_real_basemaps()
    manager = BasemapManager(BASEMAPS_PATH)
    assert manager.config["basemaps"] == basemaps

def test_init_with_missing_config(tmp_path):
    missing_path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        BasemapManager(str(missing_path))

def test_list_basemaps():
    basemaps = load_real_basemaps()
    manager = BasemapManager(BASEMAPS_PATH)
    assert manager.list_basemaps() == basemaps

def test_get_basemap_found():
    basemaps = load_real_basemaps()
    manager = BasemapManager(BASEMAPS_PATH)

    first_id = basemaps[0]["id"]
    assert manager.get_basemap(first_id) == basemaps[0]

def test_get_basemap_not_found():
    manager = BasemapManager(BASEMAPS_PATH)
    assert manager.get_basemap("does-not-exist") is None
