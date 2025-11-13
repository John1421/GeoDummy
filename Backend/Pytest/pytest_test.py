import os
import json
import pytest
import geopandas as gpd
from shapely.geometry import Point
from Backend.FileManager import FileManager

def test_copy_file_success(tmp_path):
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    src_file = src_dir / "test.txt"
    src_file.write_text("hello world")

    fm = FileManager(input_dir=str(src_dir), output_dir=str(dest_dir))
    assert fm.copy_file(str(src_file), str(dest_dir)) is True

    dest_file = dest_dir / "test.txt"
    assert dest_file.exists()
    assert dest_file.read_text() == "hello world"

def test_move_file_success(tmp_path):
    src_dir = tmp_path / "src_move"
    dest_dir = tmp_path / "dest_move"
    src_dir.mkdir()
    dest_dir.mkdir()

    src_file = src_dir / "move_me.txt"
    src_file.write_text("move")

    fm = FileManager(input_dir=str(src_dir), output_dir=str(dest_dir))
    assert fm.move_file(str(src_file), str(dest_dir)) is True

    dest_file = dest_dir / "move_me.txt"
    assert dest_file.exists()
    assert dest_file.read_text() == "move"
    assert not src_file.exists()

def test_copy_existing_destination_raises(tmp_path):
    src_dir = tmp_path / "src_conflict"
    dest_dir = tmp_path / "dest_conflict"
    src_dir.mkdir()
    dest_dir.mkdir()

    src_file = src_dir / "conflict.txt"
    src_file.write_text("one")
    existing = dest_dir / "conflict.txt"
    existing.write_text("already here")

    fm = FileManager(input_dir=str(src_dir), output_dir=str(dest_dir))
    with pytest.raises(ValueError):
        fm.copy_file(str(src_file), str(dest_dir))

def test_move_invalid_source_raises(tmp_path):
    dest_dir = tmp_path / "dest_invalid"
    dest_dir.mkdir()
    fake_source = tmp_path / "does_not_exist.txt"

    fm = FileManager(input_dir=str(tmp_path / "in_invalid"), output_dir=str(dest_dir))
    with pytest.raises(ValueError):
        fm.move_file(str(fake_source), str(dest_dir))

def test_convert_geojson_returns_same_path(tmp_path):
    gd = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "p.geojson"
    gd.to_file(str(geojson_path), driver="GeoJSON")

    fm = FileManager(input_dir=str(tmp_path), output_dir=str(tmp_path / "out"))
    returned = fm.convert_to_geojson(str(geojson_path))
    assert returned == str(geojson_path)

def test_convert_gpkg_to_geojson(tmp_path):
    gd = gpd.GeoDataFrame({'id':[1,2]}, geometry=[Point(0,0), Point(1,1)], crs="EPSG:4326")
    gpkg_path = tmp_path / "sample.gpkg"
    # gravar GeoPackage
    gd.to_file(str(gpkg_path), driver="GPKG")

    fm = FileManager(input_dir=str(tmp_path), output_dir=str(tmp_path / "out"))
    returned = fm.convert_to_geojson(str(gpkg_path))

    assert returned.lower().endswith(".geojson")
    assert os.path.isfile(returned)

    read_back = gpd.read_file(returned)
    assert len(read_back) == 2
    assert "geometry" in read_back.columns

def test_convert_unsupported_raises(tmp_path):
    txt = tmp_path / "file.txt"
    txt.write_text("not supported")
    fm = FileManager(input_dir=str(tmp_path), output_dir=str(tmp_path / "out"))
    with pytest.raises(ValueError):
        fm.convert_to_geojson(str(txt))