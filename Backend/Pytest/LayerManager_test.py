import os
import json
import pytest
import uuid
import math
import shutil
from unittest.mock import MagicMock, patch, mock_open, call
from typing import Generator

# Import the class to test
from App.LayerManager import LayerManager

# ==========================================
# FIXTURES & MOCKS
# ==========================================

@pytest.fixture
def mock_file_manager() -> Generator[MagicMock, None, None]:
    """Provides a mocked FileManager with temporary directory paths."""
    with patch('App.LayerManager.file_manager') as mock_fm:
        mock_fm.layers_dir = "/tmp/layers"
        mock_fm.temp_dir = "/tmp/temp"
        yield mock_fm

@pytest.fixture
def layer_manager(mock_file_manager: MagicMock) -> LayerManager:
    """Instantiates LayerManager with mocked environment."""
    with patch('os.listdir', return_value=[]):
        return LayerManager()

# ==========================================
# TEST SUITE
# ==========================================

class TestLayerManager:

    # --- Constructor & Integrity Tests ---

    def test_init_integrity_deletes_orphan_layers(self, mock_file_manager: MagicMock) -> None:
        """Test that orphan layer files (no metadata) are deleted on init."""
        # Setup: .gpkg exists but no _metadata.json
        files = ["layer1.gpkg", "layer2.tif", "layer2_metadata.json"]
        with patch('os.listdir', return_value=files), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            LayerManager()
            # layer1.gpkg is an orphan
            mock_remove.assert_any_call(os.path.join(mock_file_manager.layers_dir, "layer1.gpkg"))

    def test_init_integrity_deletes_orphan_metadata(self, mock_file_manager: MagicMock) -> None:
        """Test that orphan metadata files (no layer file) are deleted on init."""
        files = ["orphan_metadata.json"]
        with patch('os.listdir', return_value=files), \
             patch('os.remove') as mock_remove:
            
            LayerManager()
            mock_remove.assert_called_with(os.path.join(mock_file_manager.layers_dir, "orphan_metadata.json"))

    # --- Vector Methods ---

    @patch('geopandas.read_file')
    @patch('zipfile.ZipFile')
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_add_shapefile_zip_success(self, mock_rmtree, mock_mkdir, mock_zip, mock_gpd, 
                                       layer_manager: LayerManager) -> None:
        """Test successful import of a zipped shapefile."""
        mock_gdf = MagicMock()
        mock_gdf.crs.to_string.return_value = "EPSG:4326"
        mock_gpd.return_value = mock_gdf
        
        # Mock zip file content
        mock_zip.return_value.__enter__.return_value.namelist.return_value = ['test.shp']
        with patch('os.listdir', return_value=['test.shp']), \
             patch('os.remove'), \
             patch.object(LayerManager, '_LayerManager__get_gpkg_metadata', return_value={}), \
             patch.object(LayerManager, '_LayerManager__move_to_permanent'):
            
            res_id, meta = layer_manager.add_shapefile_zip("dummy.zip")
            
            assert isinstance(res_id, str)
            mock_gdf.to_file.assert_called()

    def test_add_shapefile_zip_no_shp_error(self, layer_manager: LayerManager) -> None:
        """Edge case: Zip file contains no .shp file."""
        with patch('zipfile.ZipFile'), \
             patch('os.makedirs'), \
             patch('os.listdir', return_value=['not_a_shp.txt']), \
             patch('os.remove'), \
             patch('shutil.rmtree'):
            
            with pytest.raises(ValueError, match="No .shp file found"):
                layer_manager.add_shapefile_zip("empty.zip")

    @patch('geopandas.read_file')
    def test_add_geojson_reprojection(self, mock_gpd, layer_manager: LayerManager) -> None:
        """Test GeoJSON import with CRS reprojection logic."""
        mock_gdf = MagicMock()
        mock_gdf.crs.to_string.return_value = "EPSG:3857" # Different from target 4326
        mock_gpd.return_value = mock_gdf
        
        with patch('os.path.isfile', return_value=True), \
             patch('os.remove'), \
             patch.object(LayerManager, '_LayerManager__get_gpkg_metadata'), \
             patch.object(LayerManager, '_LayerManager__move_to_permanent'):
            
            layer_manager.add_geojson("data.json")
            mock_gdf.to_crs.assert_called_with("EPSG:4326")

    # --- Raster Methods ---

    @patch('rasterio.open')
    def test_get_layer_information_raster(self, mock_rasterio, layer_manager: LayerManager) -> None:
        """Test retrieving metadata for a raster layer."""
        mock_src = mock_rasterio.return_value.__enter__.return_value
        mock_src.count = 3
        mock_src.width = 100
        mock_src.crs.to_string.return_value = "EPSG:4326"
        
        with patch.object(LayerManager, '_LayerManager__is_raster', return_value="path/to/raster.tif"):
            info = layer_manager.get_layer_information("my_raster")
            
            assert info['type'] == 'raster'
            assert info['bands'] == 3
            assert info['width'] == 100

    def test_add_raster_already_exists(self, layer_manager: LayerManager) -> None:
        """Edge case: Adding a raster with a name that already exists."""
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=True):
            
            with pytest.raises(ValueError, match="already exists"):
                layer_manager.add_raster("duplicate.tif")

    # --- Utility & Helper Methods ---

    def test_tile_bounds_logic(self, layer_manager: LayerManager) -> None:
        """Validate the math for XYZ tile bounding box calculation."""
        # Test Zoom 0, Tile 0,0 (Should cover the whole world)
        bounds = layer_manager.tile_bounds(0, 0, 0)
        assert bounds == (-180.0, -85.0511287798066, 180.0, 85.0511287798066)

    def test_clean_raster_cache(self, layer_manager: LayerManager) -> None:
        """
        Tests the LRU (Least Recently Used) cache eviction logic.
        Validates that the oldest files are deleted until the folder size 
        is under the limit.
        """
        cache_dir = os.path.normpath("/tmp/cache")
        
        # Files: (name, access_time, size_in_bytes)
        # We want 'old.png' to be deleted because it's the oldest and 
        # the total size (600MB) exceeds the 500MB limit.
        mock_files = [
            ("old.png", 1000, 300 * 1024 * 1024),
            ("new.png", 2000, 300 * 1024 * 1024)
        ]
        
        # Paths must be consistent with the OS running the test
        old_path = os.path.join(cache_dir, "old.png")
        new_path = os.path.join(cache_dir, "new.png")

        # Mocking os functions within the context of LayerManager
        with patch("os.walk") as mock_walk, \
             patch("os.path.getatime") as mock_atime, \
             patch("os.path.getsize") as mock_size, \
             patch("os.remove") as mock_remove:
            
            # Setup mock behavior
            mock_walk.return_value = [(cache_dir, [], ["old.png", "new.png"])]
            
            # Side effect to return specific values based on the filename passed
            def atime_side_effect(path):
                return 1000 if "old.png" in path else 2000
            
            def size_side_effect(path):
                return 300 * 1024 * 1024

            mock_atime.side_effect = atime_side_effect
            mock_size.side_effect = size_side_effect

            # Execute: Limit is 500MB, Total is 600MB
            layer_manager.clean_raster_cache(cache_dir, CACHE_MAX_BYTES=500 * 1024 * 1024)

            # Verification:
            # Check that remove was called for the oldest file
            mock_remove.assert_called_once_with(old_path)
            
            # Ensure it didn't remove the newer one
            assert call(new_path) not in mock_remove.call_args_list

    def test_clean_raster_cache_no_files(self, layer_manager: LayerManager) -> None:
        """Edge case: Cache directory is empty."""
        with patch("os.walk", return_value=[("/tmp/cache", [], [])]), \
             patch("os.remove") as mock_remove:
            
            layer_manager.clean_raster_cache("/tmp/cache")
            mock_remove.assert_not_called()

    def test_get_layer_extension_multiple_files_error(self, layer_manager: LayerManager, mock_file_manager) -> None:
        """Edge case: Multiple files match the same layer ID."""
        with patch('os.listdir', return_value=["test.gpkg", "test.tif"]):
            with pytest.raises(ValueError, match="Multiple layer files found"):
                layer_manager.get_layer_extension("test")

    def test_get_metadata_not_found(self, layer_manager: LayerManager) -> None:
        """Test metadata retrieval when file does not exist."""
        with patch('os.path.exists', return_value=False):
            assert layer_manager.get_metadata("non_existent") is None

    @patch('fiona.listlayers')
    def test_check_layer_name_exists_vector(self, mock_list, layer_manager: LayerManager) -> None:
        """Test checking if a vector layer exists in the default GPKG."""
        # Mocking default_gpkg_path which seems to be used but not explicitly defined in __init__
        # Adding it to the instance for the test
        layer_manager.default_gpkg_path = "/tmp/layers/default.gpkg"
        mock_list.return_value = ["roads", "rivers"]
        
        assert layer_manager.check_layer_name_exists("roads") is True
        assert layer_manager.check_layer_name_exists("forests") is False

# ==========================================
# MOCK EXECUTION BLOCK
# ==========================================

if __name__ == "__main__":
    # This block allows running the test file directly to see results
    print("🚀 Starting LayerManager Test Suite...")
    pytest.main([__file__, "-v", "--disable-warnings"])