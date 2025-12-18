import os
import pytest
from unittest import mock
import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import Point
import pathlib
import sys

# Ensure repo root is on sys.path so `import Backend...` works when cwd is Backend/Pytest
repo_root = pathlib.Path(__file__).resolve().parents[2]  # two levels up -> repo root
sys.path.insert(0, str(repo_root))

from Backend.LayerManager import LayerManager

@pytest.fixture(scope="module")
def mock_file_manager(tmp_path_factory):
    layers_dir = tmp_path_factory.mktemp("layers")
    temp_dir = tmp_path_factory.mktemp("temp")
    with mock.patch("Backend.LayerManager.file_manager") as fm:
        fm.layers_dir = str(layers_dir)
        fm.temp_dir = str(temp_dir)
        yield fm

@pytest.fixture(scope="module")
def layer_manager(mock_file_manager):
    with mock.patch("Backend.LayerManager.file_manager", mock_file_manager):
        yield LayerManager(default_geopackage="test_layers.gpkg")

def test_init_creates_gpkg(layer_manager, mock_file_manager):
    gpkg_path = os.path.join(mock_file_manager.layers_dir, "test_layers.gpkg")
    assert os.path.isfile(gpkg_path)

def test_add_geojson_valid(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "test.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    result = layer_manager.add_geojson(str(geojson_path), layer_name="test_layer")
    assert result == "test_layer"

def test_add_geojson_missing_file(layer_manager):
    with pytest.raises(ValueError, match="GeoJSON file does not exist"):
        layer_manager.add_geojson("not_a_file.geojson", layer_name="x")

def test_add_geojson_duplicate(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "dup.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    layer_manager.add_geojson(str(geojson_path), layer_name="dup_layer")
    with pytest.raises(ValueError, match="already exists"):
        layer_manager.add_geojson(str(geojson_path), layer_name="dup_layer")

def test_add_raster_valid(layer_manager, tmp_path):
    tif_path = tmp_path / "test.tif"
    data = np.zeros((1, 10, 10), dtype=rasterio.uint8)
    transform = rasterio.transform.from_origin(0, 10, 1, 1)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    result = layer_manager.add_raster(str(tif_path), layer_name="raster_layer")
    assert result == "raster_layer"

def test_add_raster_missing_file(layer_manager):
    with pytest.raises(ValueError, match="Raster file does not exist"):
        layer_manager.add_raster("not_a_file.tif", layer_name="x")

def test_add_raster_duplicate(layer_manager, tmp_path):
    tif_path = tmp_path / "dup.tif"
    data = np.zeros((1, 10, 10), dtype=rasterio.uint8)
    transform = rasterio.transform.from_origin(0, 10, 1, 1)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    layer_manager.add_raster(str(tif_path), layer_name="dup_raster")
    tif_path2 = tmp_path / "dup2.tif"
    with rasterio.open(
        tif_path2, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    with pytest.raises(ValueError, match="already exists"):
        layer_manager.add_raster(str(tif_path2), layer_name="dup_raster")

def test_export_geopackage_layer_to_geojson_valid(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "exp.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    layer_manager.add_geojson(str(geojson_path), layer_name="exp_layer")
    out_path = layer_manager.export_geopackage_layer_to_geojson("exp_layer")
    assert os.path.isfile(out_path)

def test_export_raster_layer_valid(layer_manager, tmp_path):
    tif_path = tmp_path / "exp.tif"
    data = np.zeros((1, 10, 10), dtype=rasterio.uint8)
    transform = rasterio.transform.from_origin(0, 10, 1, 1)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    layer_manager.add_raster(str(tif_path), layer_name="exp_raster")
    out_path = layer_manager.export_raster_layer("exp_raster")
    assert os.path.isfile(out_path)

def test_export_raster_layer_not_found(layer_manager):
    with pytest.raises(ValueError, match="not found"):
        layer_manager.export_raster_layer("not_a_raster")

def test_check_layer_name_exists(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "exists.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    layer_manager.add_geojson(str(geojson_path), layer_name="exists_layer")
    assert layer_manager.check_layer_name_exists("exists_layer")

def test_get_layer_information_vector(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "info.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    layer_manager.add_geojson(str(geojson_path), layer_name="info_layer")
    info = layer_manager.get_layer_information("info_layer")
    assert info["type"] == "vector"
    assert info["geometry_type"] == "Point"
    assert info["feature_count"] == 1

def test_get_layer_information_raster(layer_manager, tmp_path):
    tif_path = tmp_path / "info.tif"
    data = np.zeros((1, 10, 10), dtype=rasterio.uint8)
    transform = rasterio.transform.from_origin(0, 10, 1, 1)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    layer_manager.add_raster(str(tif_path), layer_name="info_raster")
    info = layer_manager.get_layer_information("info_raster")
    assert info["type"] == "raster"
    assert info["bands"] == 1
    assert info["width"] == 10
    assert info["height"] == 10

def test_get_layer_information_not_found(layer_manager):
    with pytest.raises(ValueError, match="not found"):
        layer_manager.get_layer_information("not_a_layer")

def test_get_layer_for_script_vector(layer_manager, tmp_path):
    gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs="EPSG:4326")
    geojson_path = tmp_path / "script.geojson"
    gdf.to_file(str(geojson_path), driver="GeoJSON")
    layer_manager.add_geojson(str(geojson_path), layer_name="script_layer")
    out_path = layer_manager.get_layer_for_script("script_layer")
    assert out_path is not None and out_path.endswith(".gpkg")

def test_get_layer_for_script_raster(layer_manager, tmp_path):
    tif_path = tmp_path / "script.tif"
    data = np.zeros((1, 10, 10), dtype=rasterio.uint8)
    transform = rasterio.transform.from_origin(0, 10, 1, 1)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data)
    layer_manager.add_raster(str(tif_path), layer_name="script_raster")
    out_path = layer_manager.get_layer_for_script("script_raster")
    assert out_path is not None and out_path.endswith(".tif")

def test_get_layer_for_script_not_found(layer_manager):
    assert layer_manager.get_layer_for_script("not_a_layer") is None
