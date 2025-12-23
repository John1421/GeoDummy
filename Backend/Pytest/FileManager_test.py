import os
import json
import pytest
import geopandas as gpd
from shapely.geometry import Point
import sys
import pathlib
import rasterio
from rasterio.transform import from_origin
import numpy as np

# # Ensure repo root is on sys.path so `import Backend...` works when cwd is Backend/Pytest
# repo_root = pathlib.Path(__file__).resolve().parents[2]  # two levels up -> repo root
# sys.path.insert(0, str(repo_root))

# now import the module
from App.FileManager import FileManager

def test_copy_file_success(tmp_path):
    src_dir = tmp_path / "src"
    temp_dir = tmp_path / "dest"
    src_dir.mkdir()
    temp_dir.mkdir()

    src_file = src_dir / f"test.geojson"

    # create valid file content
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    gdf.to_file(src_file)

    fm = FileManager(layers_dir=str(src_dir), temp_dir=str(temp_dir))
    assert fm.copy_file(str(src_file), str(temp_dir)) is True

    dest_file = temp_dir / f"test.geojson"
    assert dest_file.exists()

    # ensure original file still exists after copying
    assert src_file.exists()


def test_move_file_success(tmp_path):
    src_dir = tmp_path / "src_move"
    temp_dir = tmp_path / "dest_move"
    src_dir.mkdir()
    temp_dir.mkdir()

    src_file = src_dir / f"test.geojson"

    # create valid file content
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    gdf.to_file(src_file)

    fm = FileManager(layers_dir=str(src_dir), temp_dir=str(temp_dir))
    assert fm.move_file(str(src_file), str(temp_dir)) is True

    dest_file = temp_dir / f"test.geojson"
    assert dest_file.exists()

    # source file must be removed
    assert not src_file.exists()


def test_copy_existing_destination_raises(tmp_path):
    src_dir = tmp_path / "src_conflict"
    temp_dir = tmp_path / "dest_conflict"
    src_dir.mkdir()
    temp_dir.mkdir()

    src_file = src_dir / "conflict.txt"
    src_file.write_text("one")
    existing = temp_dir / "conflict.txt"
    existing.write_text("already here")

    fm = FileManager(layers_dir=str(src_dir), temp_dir=str(temp_dir))
    with pytest.raises(ValueError):
        fm.copy_file(str(src_file), str(temp_dir))

def test_move_invalid_source_raises(tmp_path):
    temp_dir = tmp_path / "dest_invalid"
    temp_dir.mkdir()
    fake_source = tmp_path / "does_not_exist.txt"

    fm = FileManager(layers_dir=str(tmp_path / "in_invalid"), temp_dir=str(temp_dir))
    with pytest.raises(ValueError):
        fm.move_file(str(fake_source), str(temp_dir))
