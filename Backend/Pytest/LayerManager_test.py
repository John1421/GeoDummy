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

    # --- get_layer_information Method Tests ---

    @patch('rasterio.open')
    def test_get_layer_information_raster_success(self, mock_rasterio_open: MagicMock, layer_manager: LayerManager) -> None:
        """Test successful metadata retrieval for a raster layer."""
        layer_id = "test_raster"
        mock_path = "/tmp/layers/test_raster.tif"
        
        # Setup mock for is_raster and rasterio
        with patch.object(layer_manager, 'is_raster', return_value=mock_path):
            mock_src = MagicMock()
            mock_src.count = 3
            mock_src.width = 100
            mock_src.height = 100
            mock_src.crs.to_string.return_value = "EPSG:4326"
            mock_src.res = (10.0, 10.0)
            mock_rasterio_open.return_value.__enter__.return_value = mock_src

            info = layer_manager.get_layer_information(layer_id)

            assert info["type"] == "raster"
            assert info["bands"] == 3
            assert info["width"] == 100
            assert info["crs"] == "EPSG:4326"

    @patch('fiona.listlayers')
    @patch('geopandas.read_file')
    @patch('os.path.isfile')
    def test_get_layer_information_vector_success(
        self, mock_isfile: MagicMock, mock_read_file: MagicMock, mock_list: MagicMock, layer_manager: LayerManager
    ) -> None:
        """
        Test successful metadata retrieval for a vector layer.
        Fixes the 'list has no attribute drop' error by mocking the columns index.
        """
        layer_id = "test_vector"
        mock_isfile.return_value = True
        mock_list.return_value = ["layer_0"]
        
        # Mock GeoDataFrame
        mock_gdf = MagicMock()
        mock_gdf.empty = False
        mock_gdf.geom_type.mode.return_value = ["Point"]
        mock_gdf.crs.to_string.return_value = "EPSG:4326"
        
        # Properly mock the columns Index and its .drop() method
        mock_columns = MagicMock()
        mock_columns.drop.return_value = ["attr1", "attr2"]
        mock_gdf.columns = mock_columns
        
        mock_gdf.__len__.return_value = 50
        mock_read_file.return_value = mock_gdf

        with patch.object(layer_manager, 'is_raster', return_value=None):
            info = layer_manager.get_layer_information(layer_id)

            assert info["type"] == "vector"
            assert info["geometry_type"] == "Point"
            assert info["attributes"] == ["attr1", "attr2"]
            assert info["feature_count"] == 50
            mock_columns.drop.assert_called_once_with("geometry")

    def test_get_layer_information_not_found(self, layer_manager: LayerManager) -> None:
        """Test that ValueError is raised if the layer exists in neither raster nor vector form."""
        with patch.object(layer_manager, 'is_raster', return_value=None), \
             patch('os.path.isfile', return_value=False):
            
            with pytest.raises(ValueError, match="not found in rasters or GeoPackage"):
                layer_manager.get_layer_information("ghost_layer")

    @patch('fiona.listlayers', side_effect=Exception("Disk Error"))
    @patch('os.path.isfile', return_value=True)
    def test_get_layer_information_gpkg_error(self, mock_isfile: MagicMock, mock_list: MagicMock, layer_manager: LayerManager) -> None:
        """Test error handling when the GeoPackage is unreadable."""
        with patch.object(layer_manager, 'is_raster', return_value=None):
            with pytest.raises(ValueError, match="Error reading GeoPackage: Disk Error"):
                layer_manager.get_layer_information("corrupt_layer")

    # --- get_layer_for_script Method Tests ---

    def test_get_layer_for_script_raster(self, layer_manager: LayerManager) -> None:
        """Test that it returns the raster path immediately if the ID is a raster."""
        mock_path = "/path/to/raster.tif"
        with patch.object(layer_manager, 'is_raster', return_value=mock_path):
            result = layer_manager.get_layer_for_script("my_raster")
            assert result == mock_path

    def test_get_layer_for_script_vector_extraction(self, layer_manager: LayerManager, mock_file_manager: MagicMock) -> None:
        """
        Fixed test: Normalizes both expected and actual paths to resolve OS-specific slash mismatches.
        """
        layer_id = "roads"
        # Force normalization of the expected path
        expected_path = os.path.normpath(os.path.join(mock_file_manager.layers_dir, f"{layer_id}.gpkg"))
        
        with patch('os.path.isfile', return_value=True), \
             patch('App.LayerManager.LayerManager.is_raster', return_value=None):
            
            result = layer_manager.get_layer_for_script(layer_id)
            
            # Use os.path.normpath on the result as well for a safe comparison
            assert os.path.normpath(result) == expected_path
            # Check that the directory part is correct
            assert os.path.normpath(mock_file_manager.layers_dir) in os.path.normpath(result)

    def test_get_layer_for_script_vector_missing(self, layer_manager: LayerManager, mock_file_manager: MagicMock) -> None:
        """
        Fixed test: Ensures it returns None when the specific .gpkg file is missing.
        """
        layer_id = "missing_vector"
        
        # Mock is_raster to return None and is_file to return False for the gpkg path
        with patch('App.LayerManager.LayerManager.is_raster', return_value=None), \
             patch('os.path.isfile', return_value=False):
            
            result = layer_manager.get_layer_for_script(layer_id)
            
            # This should now pass as the source code returns None if the file isn't found
            assert result is None
    
    def test_add_raster_already_exists(self, layer_manager: LayerManager) -> None:
        """Edge case: Adding a raster with a name that already exists."""
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=True):
            
            with pytest.raises(ValueError, match="already exists"):
                layer_manager.add_raster("duplicate.tif")

    def test_add_raster_file_not_found(self, layer_manager: LayerManager) -> None:
        """Test that ValueError is raised if the input raster file does not exist."""
        with patch('os.path.isfile', return_value=False):
            with pytest.raises(ValueError, match="Raster file does not exist."):
                layer_manager.add_raster("non_existent.tif")

    def test_add_raster_duplicate_name(self, layer_manager: LayerManager) -> None:
        """Test that ValueError is raised if a layer with the same name already exists."""
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=True):
            
            with pytest.raises(ValueError, match="already exists"):
                layer_manager.add_raster("path/to/existing_layer.tif")

    def test_add_raster_success_no_reprojection(self, layer_manager: LayerManager) -> None:
        """
        Test successful raster addition when CRS matches target (no reprojection needed).
        Validates default name extraction and metadata processing.
        """
        raster_path = "path/to/my_image.tif"
        expected_meta = {"bounds": [0, 0, 10, 10], "crs": "EPSG:4326"}
        
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=False), \
             patch.object(LayerManager, '_LayerManager__check_raster_system_coordinates', return_value="EPSG:4326"), \
             patch.object(LayerManager, '_LayerManager__get_raster_metadata', return_value=expected_meta) as mock_get_meta, \
             patch.object(LayerManager, '_LayerManager__move_to_permanent') as mock_move:
            
            res_name, res_meta = layer_manager.add_raster(raster_path)
            
            assert res_name == "my_image"  # Extracted from filename
            assert res_meta == expected_meta
            mock_move.assert_called_once_with(raster_path, "my_image", expected_meta)
            mock_get_meta.assert_called_with(raster_path, "EPSG:4326")

    def test_add_raster_success_with_reprojection(self, layer_manager: LayerManager) -> None:
        """Test successful raster addition when reprojection to EPSG:4326 is required."""
        raster_path = "source.tif"
        temp_path = "/tmp/temp_reprojected.tif"
        meta = {"info": "reprojected"}

        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=False), \
             patch.object(LayerManager, '_LayerManager__check_raster_system_coordinates', return_value="EPSG:3857"), \
             patch.object(LayerManager, '_LayerManager__convert_raster_system_coordinates', return_value=temp_path) as mock_conv, \
             patch.object(LayerManager, '_LayerManager__get_raster_metadata', return_value=meta), \
             patch.object(LayerManager, '_LayerManager__move_to_permanent') as mock_move:
            
            name, res_meta = layer_manager.add_raster(raster_path, layer_name="new_layer")
            
            assert name == "new_layer"
            mock_conv.assert_called_once_with(raster_path)
            mock_move.assert_called_once_with(temp_path, "new_layer", meta)

    def test_add_raster_conversion_failure_cleanup(self, layer_manager: LayerManager) -> None:
        """
        Test that if coordinate conversion fails, the input file is removed
        and a ValueError is raised.
        """
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=False), \
             patch.object(LayerManager, '_LayerManager__check_raster_system_coordinates', return_value="EPSG:3857"), \
             patch.object(LayerManager, '_LayerManager__convert_raster_system_coordinates', side_effect=Exception("GDAL Error")), \
             patch('os.remove') as mock_remove:
            
            with pytest.raises(ValueError, match="Failed convert raster system coordinates: GDAL Error"):
                layer_manager.add_raster("faulty.tif")
            
        # Verify cleanup was called twice
        assert mock_remove.call_count == 2
        mock_remove.assert_has_calls([call("faulty.tif"), call("faulty.tif")])

    def test_add_raster_general_exception_cleanup(self, layer_manager: LayerManager) -> None:
        """
        Test catch-all exception block. If metadata extraction fails, 
        the source file should be removed.
        """
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, 'check_layer_name_exists', return_value=False), \
             patch.object(LayerManager, '_LayerManager__check_raster_system_coordinates', return_value="EPSG:4326"), \
             patch.object(LayerManager, '_LayerManager__get_raster_metadata', side_effect=RuntimeError("Metadata error")), \
             patch('os.remove') as mock_remove:
            
            with pytest.raises(ValueError, match="Failed to add raster layer: Metadata error"):
                layer_manager.add_raster("data.tif")
            
            mock_remove.assert_called_once_with("data.tif")
    
    # --- add_gpkg_layers Method Tests ---

    @patch('geopandas.read_file')
    @patch('os.remove')
    def test_add_gpkg_layers_success_with_reprojection(
        self, 
        mock_remove: MagicMock, 
        mock_read_file: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful import of multiple layers from a GeoPackage.
        Validates:
        1. CRS normalization (reprojection).
        2. Unique UUID generation for filenames.
        3. Metadata extraction and permanent storage.
        4. Source file cleanup.
        """
        # Setup
        gpkg_path = "external_data.gpkg"
        layers = ["roads", "buildings"]
        
        # Mocking the internal helper to return two layers
        with patch.object(layer_manager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', return_value=layers):
            
            # Mock GeoDataFrame behavior
            mock_gdf = MagicMock()
            mock_gdf.crs.to_string.return_value = "EPSG:3857"  # Differs from target 4326
            mock_read_file.return_value = mock_gdf
            
            # Mock internal helpers
            mock_meta = {"feature_count": 10}
            with patch.object(layer_manager, '_LayerManager__get_gpkg_metadata', return_value=mock_meta), \
                 patch.object(layer_manager, '_LayerManager__move_to_permanent') as mock_move:
                
                ids, metadata_list = layer_manager.add_gpkg_layers(gpkg_path)

                # Assertions
                assert len(ids) == 2
                assert len(metadata_list) == 2
                assert metadata_list[0] == mock_meta
                
                # Check CRS normalization was called
                mock_gdf.to_crs.assert_called_with("EPSG:4326")
                
                # Verify permanent storage was called for both layers
                assert mock_move.call_count == 2
                
                # Verify source file was removed at the end
                mock_remove.assert_called_once_with(gpkg_path)

    @patch('geopandas.read_file')
    def test_add_gpkg_layers_missing_crs_error(
        self, 
        mock_read_file: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test that a ValueError is raised if a layer lacks CRS information.
        Ensures the exception is caught and re-raised with the specific layer name.
        """
        gpkg_path = "invalid_crs.gpkg"
        layers = ["no_crs_layer"]
        
        with patch.object(layer_manager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', return_value=layers):
            mock_gdf = MagicMock()
            mock_gdf.crs = None  # Simulate missing CRS
            mock_read_file.return_value = mock_gdf

            with pytest.raises(ValueError, match="Failed to import layer 'no_crs_layer': Layer 'no_crs_layer' has no CRS."):
                layer_manager.add_gpkg_layers(gpkg_path)

    @patch('geopandas.read_file')
    @patch('os.remove')
    def test_add_gpkg_layers_general_exception_handling(
        self, 
        mock_remove: MagicMock, 
        mock_read_file: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test that any unexpected error during processing (e.g., I/O error during to_file)
        is properly caught and raised as a ValueError.
        """
        gpkg_path = "error_prone.gpkg"
        layers = ["faulty_layer"]
        
        with patch.object(layer_manager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', return_value=layers):
            mock_gdf = MagicMock()
            mock_gdf.crs.to_string.return_value = "EPSG:4326"
            # Simulate a failure during file writing
            mock_gdf.to_file.side_effect = RuntimeError("Disk full or permission denied")
            mock_read_file.return_value = mock_gdf

            with pytest.raises(ValueError, match="Failed to import layer 'faulty_layer'"):
                layer_manager.add_gpkg_layers(gpkg_path)
            
            # Verify source file removal is NOT reached if loop breaks early via raise
            # (Note: Based on code structure, os.remove is outside the loop and won't execute if an exception is raised)
            mock_remove.assert_not_called()

    def test_add_gpkg_layers_empty_input(self, layer_manager: LayerManager) -> None:
        """
        Edge Case: Test behavior when the GeoPackage contains no spatial layers.
        Should return empty lists and still remove the source file.
        """
        gpkg_path = "empty.gpkg"
        
        with patch.object(layer_manager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', return_value=[]), \
             patch('os.remove') as mock_remove:
            
            ids, metas = layer_manager.add_gpkg_layers(gpkg_path)
            
            assert ids == []
            assert metas == []
            mock_remove.assert_called_once_with(gpkg_path)
    
    # --- export_geopackage_layer_to_geojson Method Tests ---

    @patch('fiona.listlayers')
    @patch('fiona.open')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    @patch('os.remove')
    @patch('shutil.rmtree')
    def test_export_geopackage_layer_to_geojson_success(
        self, 
        mock_rmtree: MagicMock, 
        mock_remove: MagicMock, 
        mock_isdir: MagicMock, 
        mock_isfile: MagicMock, 
        mock_listdir: MagicMock, 
        mock_makedirs: MagicMock, 
        mock_fiona_open: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager,
        mock_file_manager: MagicMock
    ) -> None:
        """
        Test successful conversion of a GeoPackage layer to GeoJSON.
        Validates:
        1. Export directory creation and cleanup of existing files/folders.
        2. Proper identification of the first layer in the GPKG.
        3. Correct feature iteration and writing to the new GeoJSON file.
        """
        layer_id = "test_layer"
        export_dir = os.path.join(mock_file_manager.temp_dir, "export")
        expected_output_path = os.path.join(export_dir, f"{layer_id}.geojson")

        # Mock directory cleanup: one file and one directory exists
        mock_listdir.return_value = ["old_file.txt", "old_subdir"]
        mock_isfile.side_effect = lambda path: "old_file.txt" in path
        mock_isdir.side_effect = lambda path: "old_subdir" in path

        # Mock fiona layer discovery
        mock_listlayers.return_value = ["layer_one"]

        # Mock fiona source and destination context managers
        mock_src = MagicMock()
        mock_src.crs = "EPSG:4326"
        mock_src.schema = {"properties": {"id": "int"}, "geometry": "Point"}
        mock_src.__iter__.return_value = [{"type": "Feature", "properties": {"id": 1}}]
        
        mock_dst = MagicMock()
        
        # side_effect to return mock_src then mock_dst for the two fiona.open calls
        mock_fiona_open.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_src)),
            MagicMock(__enter__=MagicMock(return_value=mock_dst))
        ]

        result_path = layer_manager.export_geopackage_layer_to_geojson(layer_id)

        # Assertions
        assert result_path == expected_output_path
        mock_makedirs.assert_called_once_with(export_dir, exist_ok=True)
        
        # Verify cleanup logic
        mock_remove.assert_called_once()  # For old_file.txt
        mock_rmtree.assert_called_once()  # For old_subdir
        
        # Verify writing process
        assert mock_dst.write.called
        mock_dst.write.assert_called_with({"type": "Feature", "properties": {"id": 1}})

    @patch('fiona.listlayers')
    def test_export_geopackage_layer_to_geojson_no_layers_error(
        self, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test that a ValueError is raised when the GeoPackage 
        provided has no layers inside.
        """
        mock_listlayers.return_value = [] # Empty layer list
        
        with patch('os.makedirs'), patch('os.listdir', return_value=[]):
            with pytest.raises(ValueError, match="No layers found in the GeoPackage."):
                layer_manager.export_geopackage_layer_to_geojson("empty_gpkg")

    @patch('fiona.listlayers')
    def test_export_geopackage_layer_to_geojson_fiona_exception(
        self, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test general exception handling (e.g., corrupted file or fiona error).
        Validates that the error is caught and re-raised as a descriptive ValueError.
        """
        # Simulate a crash during layer listing
        mock_listlayers.side_effect = Exception("Fiona system error")
        
        with patch('os.makedirs'), patch('os.listdir', return_value=[]):
            with pytest.raises(ValueError, match="Failed to convert GeoPackage to GeoJSON: Fiona system error"):
                layer_manager.export_geopackage_layer_to_geojson("corrupted")

    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    @patch('os.remove')
    @patch('shutil.rmtree')
    @patch('os.path.join', side_effect=os.path.join)  # Use real join logic to verify paths
    def test_export_geopackage_layer_to_geojson_cleanup_logic_only(
        self,
        mock_join: MagicMock,
        mock_rmtree: MagicMock,
        mock_remove: MagicMock,
        mock_isdir: MagicMock,
        mock_isfile: MagicMock,
        mock_listdir: MagicMock,
        layer_manager: LayerManager,
        mock_file_manager: MagicMock
    ) -> None:
        """
        Specifically tests the cleanup loop to ensure it handles mixed 
        files and directories in the export folder correctly.
        """
        # Define paths relative to the mock file manager
        export_dir = os.path.join(mock_file_manager.temp_dir, "export")
        file_to_delete = "f1.txt"
        dir_to_delete = "d1_dir"
        
        mock_listdir.return_value = [file_to_delete, dir_to_delete]
        
        # Configure mocks to identify f1 as a file and d1 as a directory
        mock_isfile.side_effect = lambda p: file_to_delete in p
        mock_isdir.side_effect = lambda p: dir_to_delete in p
        
        # Stop execution after the cleanup loop by forcing an error on the next line
        with patch('os.makedirs'), \
             patch('fiona.listlayers', side_effect=RuntimeError("Interrupt")):
            
            try:
                layer_manager.export_geopackage_layer_to_geojson("test_id")
            except ValueError:
                pass # This catch is expected due to the 'Interrupt'
            
            # Verify the exact paths were targeted for removal
            expected_file_path = os.path.join(export_dir, file_to_delete)
            expected_dir_path = os.path.join(export_dir, dir_to_delete)
            
            mock_remove.assert_called_once_with(expected_file_path)
            mock_rmtree.assert_called_once_with(expected_dir_path)

    # --- Utility & Helper Methods ---

    # --- __check_raster_system_coordinates Method Tests ---

    @patch('rioxarray.open_rasterio')
    def test_check_raster_system_coordinates_success(
        self, 
        mock_open_rasterio: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful CRS extraction from a raster file.
        Validates that the CRS is correctly returned as a string.
        """
        raster_path = "valid_raster.tif"
        expected_crs = "EPSG:4326"
        
        # Mock the context manager and the rio.crs object
        mock_raster = MagicMock()
        mock_raster.rio.crs.to_string.return_value = expected_crs
        mock_open_rasterio.return_value.__enter__.return_value = mock_raster

        # Access the private method via name mangling
        result = layer_manager._LayerManager__check_raster_system_coordinates(raster_path)

        assert result == expected_crs
        mock_open_rasterio.assert_called_once_with(raster_path)

    @patch('rioxarray.open_rasterio')
    def test_check_raster_system_coordinates_no_crs_error(
        self, 
        mock_open_rasterio: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test that a ValueError is raised when the raster lacks CRS info.
        Note: The inner ValueError is caught by the outer block and re-raised.
        """
        raster_path = "no_crs.tif"
        
        # Mock raster with None for CRS
        mock_raster = MagicMock()
        mock_raster.rio.crs = None
        mock_open_rasterio.return_value.__enter__.return_value = mock_raster

        expected_error_msg = "Error checking tif CRS: Raster has no CRS information."
        
        with pytest.raises(ValueError, match=expected_error_msg):
            layer_manager._LayerManager__check_raster_system_coordinates(raster_path)

    @patch('rioxarray.open_rasterio')
    def test_check_raster_system_coordinates_open_failure(
        self, 
        mock_open_rasterio: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test that general exceptions (e.g., file corruption or I/O error) 
        are correctly caught and re-raised as a descriptive ValueError.
        """
        raster_path = "corrupted.tif"
        
        # Simulate an unexpected exception during file opening
        mock_open_rasterio.side_effect = RuntimeError("Low level I/O error")

        expected_error_msg = "Error checking tif CRS: Low level I/O error"
        
        with pytest.raises(ValueError, match=expected_error_msg):
            layer_manager._LayerManager__check_raster_system_coordinates(raster_path)

    # --- __convert_raster_system_coordinates Method Tests ---

    @patch('shutil.copy')
    @patch('os.remove')
    @patch('rioxarray.open_rasterio')
    def test_convert_raster_system_coordinates_success(
        self, 
        mock_open_rasterio: MagicMock, 
        mock_remove: MagicMock, 
        mock_copy: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful raster CRS conversion.
        Validates that:
        1. A temporary file is created via shutil.copy.
        2. The raster is reprojected and saved to the original path.
        3. The temporary file is cleaned up.
        """
        raster_path = "original.tif"
        target_crs = "EPSG:4326"
        temp_path = "very_complex_raster_name_temp.tiff"

        # Mock rioxarray flow
        mock_raster = MagicMock()
        mock_converted = MagicMock()
        
        # Setup context manager and reprojection chain
        mock_open_rasterio.return_value.__enter__.return_value = mock_raster
        mock_raster.rio.reproject.return_value = mock_converted

        # Execute private static method
        result = LayerManager._LayerManager__convert_raster_system_coordinates(raster_path, target_crs)

        # Assertions
        assert result == raster_path
        mock_copy.assert_called_once_with(raster_path, temp_path)
        mock_raster.rio.reproject.assert_called_once_with(target_crs)
        mock_converted.rio.to_raster.assert_called_once_with(raster_path)
        mock_remove.assert_called_once_with(temp_path)

    @patch('shutil.copy')
    @patch('rioxarray.open_rasterio')
    def test_convert_raster_system_coordinates_failure(
        self, 
        mock_open_rasterio: MagicMock, 
        mock_copy: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test exception handling during raster conversion.
        Validates that a ValueError is raised when reprojection logic fails.
        """
        raster_path = "faulty.tif"
        
        # Simulate a failure during the reprojection step
        mock_raster = MagicMock()
        mock_raster.rio.reproject.side_effect = Exception("Projection engine failed")
        mock_open_rasterio.return_value.__enter__.return_value = mock_raster

        # Verify the exception is wrapped in a ValueError with the correct prefix
        with pytest.raises(ValueError, match="Error converting tif CRS: Projection engine failed"):
            LayerManager._LayerManager__convert_raster_system_coordinates(raster_path)

    @patch('shutil.copy', side_effect=OSError("Permission denied"))
    def test_convert_raster_system_coordinates_copy_failure(
        self, 
        mock_copy: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test failure at the initial file system level (copying).
        
        Note: Because shutil.copy is called before the try block in the source code,
        this will raise the raw OSError rather than a ValueError.
        """
        # We expect OSError here because it occurs on line 2 of the method,
        # which is outside the try/except block.
        with pytest.raises(OSError, match="Permission denied"):
            LayerManager._LayerManager__convert_raster_system_coordinates("source.tif")

    # --- __retrieve_spatial_layers_from_incoming_gpkg Method Tests ---

    @patch('fiona.listlayers')
    @patch('fiona.open')
    def test_retrieve_spatial_layers_success(
        self, 
        mock_fiona_open: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful retrieval and filtering of spatial layers.
        Validates:
        1. Correctly identifies layers with valid geometry.
        2. Correctly skips layers with None or empty geometry strings.
        """
        gpkg_path = "valid_data.gpkg"
        # List of layers: spatial, non-spatial (None), and non-spatial ("None")
        mock_listlayers.return_value = ["spatial_layer", "table_layer", "ghost_layer"]

        # Define schema responses for the three layers
        mock_src_spatial = MagicMock()
        mock_src_spatial.schema = {"geometry": "Point"}
        
        mock_src_table = MagicMock()
        mock_src_table.schema = {"geometry": None}
        
        mock_src_ghost = MagicMock()
        mock_src_ghost.schema = {"geometry": "None"}

        # Configure fiona.open to return different contexts based on the layer requested
        mock_fiona_open.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_src_spatial)),
            MagicMock(__enter__=MagicMock(return_value=mock_src_table)),
            MagicMock(__enter__=MagicMock(return_value=mock_src_ghost))
        ]

        result = LayerManager._LayerManager__retrieve_spatial_layers_from_incoming_gpkg(gpkg_path)

        assert result == ["spatial_layer"]
        assert len(result) == 1
        assert mock_fiona_open.call_count == 3

    @patch('fiona.listlayers')
    def test_retrieve_spatial_layers_invalid_gpkg(
        self, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """Test that a corrupted or invalid file raises a descriptive ValueError."""
        mock_listlayers.side_effect = Exception("File format not recognized")
        
        with pytest.raises(ValueError, match="Invalid GeoPackage: File format not recognized"):
            LayerManager._LayerManager__retrieve_spatial_layers_from_incoming_gpkg("corrupt.gpkg")

    @patch('fiona.listlayers')
    def test_retrieve_spatial_layers_empty_gpkg(
        self, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """Test that a GeoPackage with zero layers raises an error."""
        mock_listlayers.return_value = []
        
        with pytest.raises(ValueError, match="GeoPackage contains no layers."):
            LayerManager._LayerManager__retrieve_spatial_layers_from_incoming_gpkg("empty.gpkg")

    @patch('fiona.listlayers')
    @patch('fiona.open')
    def test_retrieve_spatial_layers_no_valid_spatial_found(
        self, 
        mock_fiona_open: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test edge case where layers exist but none are spatial.
        Ensures the final ValueError is raised if the filtered list is empty.
        """
        mock_listlayers.return_value = ["metadata_table"]
        
        mock_src = MagicMock()
        mock_src.schema = {"geometry": ""}  # Empty geometry string
        mock_fiona_open.return_value.__enter__.return_value = mock_src

        with pytest.raises(ValueError, match="No valid spatial layers found in GeoPackage."):
            LayerManager._LayerManager__retrieve_spatial_layers_from_incoming_gpkg("tables_only.gpkg")

    @patch('fiona.listlayers')
    @patch('fiona.open')
    def test_retrieve_spatial_layers_handles_fiona_errors_gracefully(
        self, 
        mock_fiona_open: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test that individual layer reading errors (FionaValueError or general Exception)
        do not crash the process and simply cause the layer to be skipped.
        """
        mock_listlayers.return_value = ["error_layer", "good_layer"]
        
        # First call fails, second call succeeds
        mock_src_good = MagicMock()
        mock_src_good.schema = {"geometry": "Polygon"}
        
        # We need to import FionaValueError or mock it if not available in context
        # Assuming it's accessible via fiona
        from fiona.errors import FionaValueError

        mock_fiona_open.side_effect = [
            FionaValueError("Cannot read extent"),
            MagicMock(__enter__=MagicMock(return_value=mock_src_good))
        ]

        result = LayerManager._LayerManager__retrieve_spatial_layers_from_incoming_gpkg("mixed.gpkg")

        assert result == ["good_layer"]
        assert len(result) == 1

    # --- __get_gpkg_metadata Method Tests ---

    @patch('fiona.listlayers')
    @patch('geopandas.read_file')
    def test_get_gpkg_metadata_success(
        self, 
        mock_read_file: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful metadata extraction from a GeoPackage.
        Validates the mapping of geometry type, CRS, attributes, and bounding box.
        """
        gpkg_path = "data.gpkg"
        crs_original = "EPSG:3857"
        mock_listlayers.return_value = ["layer_one"]

        # Mock GeoDataFrame
        mock_gdf = MagicMock()
        mock_gdf.empty = False
        mock_gdf.geom_type.mode.return_value = ["Polygon"]
        mock_gdf.crs.to_string.return_value = "EPSG:4326"
        mock_gdf.total_bounds = MagicMock()
        mock_gdf.total_bounds.tolist.return_value = [0.0, 0.0, 1.0, 1.0]
        mock_gdf.__len__.return_value = 100

        # Correctly mock columns Index to handle .drop("geometry")
        mock_columns = MagicMock()
        mock_columns.drop.return_value = ["id", "name"]
        mock_gdf.columns = mock_columns

        mock_read_file.return_value = mock_gdf

        result = LayerManager._LayerManager__get_gpkg_metadata(gpkg_path, crs_original)

        assert result["layer_name"] == "layer_one"
        assert result["type"] == "vector"
        assert result["geometry_type"] == "Polygon"
        assert result["crs_original"] == crs_original
        assert result["attributes"] == ["id", "name"]
        assert result["feature_count"] == 100
        assert result["bounding_box"] == [0.0, 0.0, 1.0, 1.0]

    @patch('fiona.listlayers')
    @patch('geopandas.read_file')
    def test_get_gpkg_metadata_empty_gdf(
        self, 
        mock_read_file: MagicMock, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test metadata extraction when the GeoDataFrame is empty.
        Ensures geometry_type returns None instead of crashing.
        """
        mock_listlayers.return_value = ["empty_layer"]
        
        mock_gdf = MagicMock()
        mock_gdf.empty = True
        mock_gdf.crs = None
        mock_gdf.total_bounds.tolist.return_value = []
        mock_gdf.__len__.return_value = 0
        
        mock_columns = MagicMock()
        mock_columns.drop.return_value = []
        mock_gdf.columns = mock_columns
        
        mock_read_file.return_value = mock_gdf

        result = LayerManager._LayerManager__get_gpkg_metadata("empty.gpkg", "EPSG:4326")

        assert result["geometry_type"] is None
        assert result["crs"] is None
        assert result["feature_count"] == 0

    @patch('fiona.listlayers', side_effect=Exception("Fiona read error"))
    def test_get_gpkg_metadata_exception(
        self, 
        mock_listlayers: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test exception handling when reading the GeoPackage fails.
        Validates that errors are caught and re-raised as ValueErrors with the correct prefix.
        """
        with pytest.raises(ValueError, match="Error reading GeoPackage: Fiona read error"):
            LayerManager._LayerManager__get_gpkg_metadata("corrupt.gpkg", "EPSG:4326")

    # --- __get_raster_metadata Method Tests ---

    @patch('rasterio.open')
    @patch('App.LayerManager.transform_bounds')
    def test_get_raster_metadata_success(
        self, 
        mock_transform_bounds: MagicMock, 
        mock_rasterio_open: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test successful extraction of raster metadata.
        Validates:
        1. Correct calculation of zoom_min and zoom_max based on pixel size.
        2. Proper mapping of raster properties (bands, width, height, res).
        3. Successful integration with transform_bounds for bbox generation.
        """
        raster_path = "test_raster.tif"
        crs_original = "EPSG:32631"
        
        # Mock Raster Source
        mock_src = MagicMock()
        # Affine transform: a=pixel_size_x, e=pixel_size_y (negative)
        mock_src.transform.a = 0.5
        mock_src.transform.e = -0.5
        mock_src.width = 1000
        mock_src.height = 1000
        mock_src.count = 3
        mock_src.res = (0.5, 0.5)
        mock_src.crs.to_string.return_value = "EPSG:4326"
        mock_src.bounds.left = 0
        mock_src.bounds.bottom = 0
        mock_src.bounds.right = 500
        mock_src.bounds.top = 500
        
        mock_rasterio_open.return_value.__enter__.return_value = mock_src
        
        # Mock transform_bounds return (min_lon, min_lat, max_lon, max_lat)
        mock_transform_bounds.return_value = (-1.0, -1.0, 1.0, 1.0)

        # Execute private static method via name mangling
        metadata = LayerManager._LayerManager__get_raster_metadata(raster_path, crs_original)

        # Assertions
        assert metadata["type"] == "raster"
        assert metadata["crs_original"] == crs_original
        assert metadata["bands"] == 3
        assert metadata["width"] == 1000
        assert metadata["bbox"]["min_lon"] == -1.0
        
        # Verify zoom calculations
        # pixel_size = 0.5. zoom_max = ceil(log2(360 / (256 * 0.5))) = ceil(log2(2.8125)) = 2
        assert metadata["zoom_max"] == 2
        # raster_extent = 0.5 * 1000 = 500. zoom_min = max(0, floor(log2(360 / (256 * 500)))) = 0
        assert metadata["zoom_min"] == 0

        mock_transform_bounds.assert_called_once()

    @patch('rasterio.open')
    @patch('App.LayerManager.transform_bounds')
    def test_get_raster_metadata_no_crs(
        self, 
        mock_transform_bounds: MagicMock, 
        mock_rasterio_open: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test metadata extraction when the raster has no CRS defined.
        Ensures all numeric attributes are mocked to prevent TypeError during math comparisons.
        """
        mock_src = MagicMock()
        mock_src.crs = None
        # Mocking all numeric attributes used in internal calculations (max/min/log2)
        mock_src.transform.a = 1.0
        mock_src.transform.e = -1.0
        mock_src.width = 512
        mock_src.height = 512
        mock_src.count = 1
        mock_src.res = (1.0, 1.0)
        mock_src.bounds.left = 0
        mock_src.bounds.bottom = 0
        mock_src.bounds.right = 512
        mock_src.bounds.top = 512
        
        mock_rasterio_open.return_value.__enter__.return_value = mock_src
        mock_transform_bounds.return_value = (0, 0, 0, 0)

        metadata = LayerManager._LayerManager__get_raster_metadata("no_crs.tif", "None")

        assert metadata["crs"] is None
        assert metadata["type"] == "raster"
        assert "zoom_min" in metadata
        assert "zoom_max" in metadata

    @patch('rasterio.open', side_effect=Exception("File not readable"))
    def test_get_raster_metadata_exception(
        self, 
        mock_rasterio_open: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test that exceptions during raster opening are correctly propagated.
        """
        with pytest.raises(Exception, match="File not readable"):
            LayerManager._LayerManager__get_raster_metadata("broken.tif", "EPSG:4326")
    
    # --- __move_to_permanent Method Tests ---

    @patch('shutil.move')
    @patch('os.path.isfile')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_move_to_permanent_success(
        self,
        mock_json_dump: MagicMock,
        mock_file_open: MagicMock,
        mock_isfile: MagicMock,
        mock_shutil_move: MagicMock,
        layer_manager: LayerManager,
        mock_file_manager: MagicMock
    ) -> None:
        """
        Test successful migration of a layer and its metadata to permanent storage.
        Validates:
        1. Correct destination path construction based on file extension.
        2. shutil.move is called correctly.
        3. Metadata is serialized to the correct JSON path.
        """
        temp_path = "/tmp/temp/new_layer.gpkg"
        layer_id = "permanent_layer_123"
        metadata = {"type": "vector", "feature_count": 10}
        
        # Mocking existence check
        mock_isfile.return_value = True
        
        # Execute private static method
        LayerManager._LayerManager__move_to_permanent(temp_path, layer_id, metadata)

        # Verify file move
        expected_dest = os.path.join(mock_file_manager.layers_dir, f"{layer_id}.gpkg")
        mock_shutil_move.assert_called_once_with(temp_path, expected_dest)

        # Verify metadata save
        expected_meta_path = os.path.join(mock_file_manager.layers_dir, f"{layer_id}_metadata.json")
        mock_file_open.assert_called_once_with(expected_meta_path, 'w')
        mock_json_dump.assert_called_once_with(metadata, mock_file_open(), indent=4)

    @patch('os.path.isfile', return_value=False)
    def test_move_to_permanent_source_not_found(
        self, 
        mock_isfile: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Edge Case: Test that a ValueError is raised if the source temporary file 
        does not exist before the move operation.
        """
        temp_path = "/non/existent/file.tif"
        
        with pytest.raises(ValueError, match=f"Source file not found: {temp_path}"):
            LayerManager._LayerManager__move_to_permanent(temp_path, "id", {})

    @patch('os.path.isfile', return_value=True)
    @patch('shutil.move', side_effect=PermissionError("Access Denied"))
    def test_move_to_permanent_move_failure(
        self, 
        mock_move: MagicMock, 
        mock_isfile: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test exception handling during the shutil.move operation.
        Ensures OS errors are caught and re-raised with a descriptive message.
        """
        with pytest.raises(ValueError, match="Failed to move layer to permanent storage: Access Denied"):
            LayerManager._LayerManager__move_to_permanent("source.tif", "id", {})

    @patch('os.path.isfile', return_value=True)
    @patch('shutil.move')
    @patch('builtins.open', side_effect=Exception("Disk Full"))
    def test_move_to_permanent_metadata_save_failure(
        self, 
        mock_open: MagicMock, 
        mock_move: MagicMock, 
        mock_isfile: MagicMock, 
        layer_manager: LayerManager
    ) -> None:
        """
        Test exception handling during metadata JSON creation.
        Ensures that if the file move succeeds but the metadata save fails,
        the appropriate ValueError is raised.
        """
        with pytest.raises(ValueError, match="Failed to save layer metadata: Disk Full"):
            LayerManager._LayerManager__move_to_permanent("source.tif", "id", {"key": "val"})

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

    # --- get_geopackage_layers Method Tests ---

    def test_get_geopackage_layers_file_not_found(self, layer_manager: LayerManager) -> None:
        """
        Test that ValueError is raised when the gpkg_path does not exist.
        Covers the 'if not os.path.isfile' branch.
        """
        with patch('os.path.isfile', return_value=False):
            with pytest.raises(ValueError, match="GeoPackage file does not exist."):
                layer_manager.get_geopackage_layers("non_existent.gpkg")

    def test_get_geopackage_layers_success(self, layer_manager: LayerManager) -> None:
        """
        Test successful retrieval of spatial layers.
        Covers the main success path.
        """
        gpkg_path = "valid.gpkg"
        expected_layers = ["layer1", "layer2"]
        
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', 
                          return_value=expected_layers):
            
            result = layer_manager.get_geopackage_layers(gpkg_path)
            assert result == expected_layers

    def test_get_geopackage_layers_re_raises_value_error(self, layer_manager: LayerManager) -> None:
        """
        Test that specific ValueErrors from the internal helper are re-raised.
        Covers the 'except ValueError as e: raise e' branch.
        """
        gpkg_path = "empty.gpkg"
        error_msg = "contains no spatial layers"
        
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', 
                          side_effect=ValueError(error_msg)):
            
            with pytest.raises(ValueError, match=error_msg):
                layer_manager.get_geopackage_layers(gpkg_path)

    def test_get_geopackage_layers_generic_exception(self, layer_manager: LayerManager) -> None:
        """
        Test that unexpected exceptions are caught and wrapped in a ValueError.
        Covers the 'except Exception as e' branch.
        """
        gpkg_path = "corrupt.gpkg"
        original_error = "Low level driver error"
        
        with patch('os.path.isfile', return_value=True), \
             patch.object(LayerManager, '_LayerManager__retrieve_spatial_layers_from_incoming_gpkg', 
                          side_effect=RuntimeError(original_error)):
            
            with pytest.raises(ValueError, match=f"Error reading GeoPackage: {original_error}"):
                layer_manager.get_geopackage_layers(gpkg_path)   

    # --- add_shapefile_zip Method Tests ---

    def test_add_shapefile_zip_unzip_failure(self, layer_manager: LayerManager) -> None:
        """
        Test branch: "Error unzipping shapefile".
        Triggers exception during zip extraction and ensures cleanup of the zip file.
        """
        zip_path = "/tmp/test.zip"
        with patch('zipfile.ZipFile', side_effect=Exception("Corrupt Zip")), \
             patch('os.remove') as mock_remove:
            
            with pytest.raises(ValueError, match="Error unzipping shapefile: Corrupt Zip"):
                layer_manager.add_shapefile_zip(zip_path)
            
            # Verify cleanup of the zip file after failure
            mock_remove.assert_called_once_with(zip_path)

    def test_add_shapefile_zip_delete_zip_failure(self, layer_manager: LayerManager) -> None:
        """
        Test branch: "Failed to delete the zip file after extraction".
        Triggers exception when trying to remove the zip file after successful extraction.
        """
        zip_path = "/tmp/test.zip"
        # Mocking os.remove specifically for the second try-block
        with patch('zipfile.ZipFile'), \
             patch('os.listdir', return_value=['test.shp']), \
             patch('os.remove', side_effect=Exception("Permission Denied")):
            
            with pytest.raises(ValueError, match="Failed to delete the zip file after extraction: Permission Denied"):
                layer_manager.add_shapefile_zip(zip_path)

    def test_add_shapefile_zip_geopandas_read_failure(self, layer_manager: LayerManager) -> None:
        """
        Test branch: "Error reading shapefile with GeoPandas:".
        Triggers exception during gpd.read_file and ensures temp directory cleanup.
        """
        with patch('zipfile.ZipFile'), \
             patch('os.remove'), \
             patch('os.listdir', return_value=['valid.shp']), \
             patch('geopandas.read_file', side_effect=Exception("Fiona Error")), \
             patch('shutil.rmtree') as mock_rmtree:
            
            with pytest.raises(ValueError, match="Error reading shapefile with GeoPandas: Fiona Error"):
                layer_manager.add_shapefile_zip("test.zip")
            
            # Verify extracted files are cleaned up
            mock_rmtree.assert_called_with(os.path.join("/tmp/temp", "shp_extracted"))

    def test_add_shapefile_zip_no_crs(self, layer_manager: LayerManager) -> None:
        """
        Test branch: "Shapefile has no CRS defined (.prj missing or unreadable).".
        Triggers branch where gdf.crs is None.
        """
        mock_gdf = MagicMock()
        mock_gdf.crs = None
        
        with patch('zipfile.ZipFile'), \
             patch('os.remove'), \
             patch('os.listdir', return_value=['test.shp']), \
             patch('geopandas.read_file', return_value=mock_gdf), \
             patch('shutil.rmtree') as mock_rmtree:
            
            with pytest.raises(ValueError, match="Shapefile has no CRS defined"):
                layer_manager.add_shapefile_zip("test.zip")
            
            mock_rmtree.assert_called_with(os.path.join("/tmp/temp", "shp_extracted"))

    def test_add_shapefile_zip_reprojection_and_success(self, layer_manager: LayerManager) -> None:
        """
        Test branch: # 6. Reproject if needed.
        Covers the branch where original_crs != target_crs and successful completion.
        """
        # Setup mock GDF with a different CRS than EPSG:4326
        mock_gdf = MagicMock()
        mock_gdf.crs.to_string.return_value = "EPSG:3857"
        mock_metadata = {"crs": "EPSG:4326", "bounds": [0, 0, 1, 1]}
        
        with patch('zipfile.ZipFile'), \
             patch('os.remove'), \
             patch('os.listdir', return_value=['test.shp']), \
             patch('geopandas.read_file', return_value=mock_gdf), \
             patch.object(LayerManager, '_LayerManager__get_gpkg_metadata', return_value=mock_metadata), \
             patch.object(LayerManager, '_LayerManager__move_to_permanent'):
            
            layer_id, metadata = layer_manager.add_shapefile_zip("test.zip", target_crs="EPSG:4326")
            
            # Verify to_crs was called because EPSG:3857 != EPSG:4326
            mock_gdf.to_crs.assert_called_once_with("EPSG:4326")
            assert metadata == mock_metadata

    def test_add_shapefile_zip_writing_failure(self, layer_manager: LayerManager) -> None:
        """
        Test branch: "Error writing shapefile into GeoPackage: {e}".
        Triggers exception during the gdf.to_file or metadata processing phase.
        """
        mock_gdf = MagicMock()
        mock_gdf.crs.to_string.return_value = "EPSG:4326"
        
        with patch('zipfile.ZipFile'), \
             patch('os.remove'), \
             patch('os.listdir', return_value=['test.shp']), \
             patch('geopandas.read_file', return_value=mock_gdf):
            
            # Simulate failure during the writing process
            mock_gdf.to_file.side_effect = Exception("Disk Full")
            
            with pytest.raises(ValueError, match="Error writing shapefile into GeoPackage: Disk Full"):
                layer_manager.add_shapefile_zip("test.zip")
    

# ==========================================
# MOCK EXECUTION BLOCK
# ==========================================

if __name__ == "__main__":
    # This block allows running the test file directly to see results
    print("🚀 Starting LayerManager Test Suite...")
    pytest.main([__file__, "-v", "--disable-warnings"])