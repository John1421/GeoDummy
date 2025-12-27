import pytest
import json
import io
import os
import numpy as np
from unittest.mock import MagicMock, patch
from flask import Flask
from werkzeug.exceptions import BadRequest, NotFound

# Import the app instance. Assuming the structure allows 'from app import app'
from App.app import app

class TestApp:
    """
    Test suite for the GeoDummy backend application.
    Covers script management, layer interactions, and general API error handling.
    """

    @pytest.fixture
    def client(self):
        """Configures the Flask test client for the app."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_managers(self):
        """
        Mocks all manager instances and global dependencies used in app.py.
        This isolates the API logic from filesystem or database side effects.
        """
        with patch('App.app.file_manager') as mock_fm, \
             patch('App.app.basemap_manager') as mock_bm, \
             patch('App.app.layer_manager') as mock_lm, \
             patch('App.app.script_manager') as mock_sm, \
             patch('App.app.data_manager') as mock_dm:
            
            # Setup common mock attributes
            mock_fm.temp_dir = "/tmp"
            mock_fm.scripts_dir = "/scripts"
            mock_lm.MAX_LAYER_FILE_SIZE = 100 * 1024 * 1024
            
            yield {
                "file": mock_fm,
                "basemap": mock_bm,
                "layer": mock_lm,
                "script": mock_sm,
                "data": mock_dm
            }

    # --- General / Error Handling Tests ---

    def test_home_endpoint(self, client):
        """Validates that the home route is running."""
        response = client.get('/')
        assert response.status_code == 200
        assert b"GeoDummy backend is running" in response.data

    def test_generic_exception_handler(self, client, mock_managers):
        """Tests the global exception handler when an unexpected error occurs."""
        mock_managers["basemap"].list_basemaps.side_effect = Exception("Unexpected failure")
        response = client.get('/basemaps')
        assert response.status_code == 500
        data = response.get_json()
        assert data["error"]["message"] == "Internal Server Error"

    # --- Script Management Tests ---

    def test_add_script_no_file(self, client):
        """Edge case: Ensures error when no file is provided in multipart form."""
        response = client.post('/scripts', data={})
        assert response.status_code == 400
        assert b"upload a file" in response.data

    def test_add_script_success(self, client, mock_managers):
        """Normal path: Successfully adding a valid python script."""
        mock_managers["script"].check_script_name_exists.return_value = False
        
        data = {
            'file': (io.BytesIO(b"print('hello')"), 'test_script.py'),
            'param1': 'value1'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 200
        assert response.get_json()["script_id"] == "test_script"
        mock_managers["file"].move_file.assert_called()

    def test_add_script_invalid_extension(self, client, mock_managers):
        """Boundary condition: Rejecting non-python files."""
        data = {
            'file': (io.BytesIO(b"some content"), 'test.txt'),
            'p': 'v'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert b"only accepts python scripts" in response.data

    # --- Layer Management Tests ---

    @pytest.mark.parametrize("extension, method", [
        (".zip", "add_shapefile_zip"),
        (".geojson", "add_geojson"),
        (".gpkg", "add_gpkg_layers")
    ])
    def test_add_layer_various_formats(self, client, mock_managers, extension, method):
        """Parametrized test to verify different file formats trigger correct manager methods."""
        mock_managers["layer"].check_layer_name_exists.return_value = False
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        
        # Mock return values for specific methods
        getattr(mock_managers["layer"], method).return_value = ("layer1", {"meta": "data"})

        file_name = f"my_data{extension}"
        data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
        
        with patch('os.path.getsize', return_value=10):
            response = client.post('/layers', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 200
        assert "layer1" in response.get_json()["layer_id"]
        getattr(mock_managers["layer"], method).assert_called_once()

    def test_add_layer_size_exceeded(self, client, mock_managers):
        """Error handling: Rejects files larger than MAX_LAYER_FILE_SIZE."""
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 50
        data = {'file': (io.BytesIO(b"a" * 100), 'large.geojson')}
        
        with patch('os.path.getsize', return_value=100):
            response = client.post('/layers', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        assert b"exceeds the maximum allowed size" in response.data

    # --- Data Interaction Tests ---

    def test_get_layer_attributes_success(self, client, mock_managers):
        """Validates successful retrieval of layer attributes."""
        mock_managers["layer"].get_metadata.return_value = {"attributes": {"attr1": "val1"}}
        
        response = client.get('/layers/layer123/attributes')
        assert response.status_code == 200
        assert response.get_json()["attributes"]["attr1"] == "val1"

    def test_extract_data_for_table_view_cached(self, client, mock_managers):
        """Test behavior: Returns cached data if available to save computation."""
        cached_response = {"headers": [], "rows": [], "total_rows": 0, "warnings": []}
        mock_managers["data"].check_cache.return_value = cached_response
        mock_managers["layer"]._LayerManager__is_raster.return_value = False

        response = client.get('/layers/layer_id/table')
        assert response.status_code == 200
        assert response.get_json() == cached_response
        # Ensure it didn't call the heavy metadata logic
        mock_managers["layer"].get_metadata.assert_not_called()

    # --- Script Execution Tests ---

    def test_run_script_already_running(self, client, mock_managers):
        """Edge case: Prevents running a script that is already in 'running' status."""
        from App.app import running_scripts
        with patch('App.app.running_scripts', {"script1": {"status": "running"}}):
            response = client.post('/scripts/script1', json={"parameters": {}})
            assert response.status_code == 400
            assert b"already running" in response.data

    def test_run_script_not_found(self, client, mock_managers):
        """Error handling: Rejects execution of scripts that don't exist on disk."""
        with patch('os.path.isfile', return_value=False):
            response = client.post('/scripts/missing_script', json={"parameters": {}})
            assert response.status_code == 400
            assert b"does not exist" in response.data

    # --- Map / Tile Interaction Tests ---

    def test_serve_tile_from_cache(self, client, mock_managers):
        """Validates that tiles are served from cache if they exist."""
        with patch('os.path.exists', return_value=True), \
             patch('App.app.send_file') as mock_send:
            
            client.get('/layers/layer1/tiles/1/2/3.png')
            # Check that the cache file path was constructed correctly
            args, _ = mock_send.call_args
            assert "layer1_1_2_3.png" in args[0]

    def test_list_basemaps_success(self, client, mock_managers):
        """Normal execution: Lists available basemaps."""
        mock_managers["basemap"].list_basemaps.return_value = [{"id": "bm1", "name": "Basemap 1"}]
        response = client.get('/basemaps')
        assert response.status_code == 200
        assert len(response.get_json()) == 1

    # --- Tests for GET /scripts/<script_id> ---

    def test_script_metadata_success(self, client, mock_managers):
        """
        Tests successful retrieval of script metadata.
        Validates the 200 OK response and JSON structure.
        """
        mock_sm = mock_managers["script"]
        expected_metadata = {"params": {"a": "int"}, "description": "test script"}
        mock_sm.get_metadata.return_value = expected_metadata

        response = client.get('/scripts/test_script_123')

        assert response.status_code == 200
        data = response.get_json()
        assert data["script_id"] == "test_script_123"
        assert data["output"] == expected_metadata
        mock_sm.get_metadata.assert_called_once_with("test_script_123")

    def test_script_metadata_not_found(self, client, mock_managers):
        """
        Tests behavior when the metadata file does not exist.
        Covers the FileNotFoundError exception path leading to a 404.
        """
        mock_sm = mock_managers["script"]
        mock_sm.get_metadata.side_effect = FileNotFoundError()

        response = client.get('/scripts/non_existent_script')

        assert response.status_code == 404
        # Flask's default or custom error handler returns a 404 for NotFound exceptions
        assert "Metadata not found" in str(response.data)

    def test_script_metadata_value_error(self, client, mock_managers):
        """
        Tests behavior when metadata parsing fails.
        Covers the ValueError exception path leading to a 400 BadRequest.
        """
        mock_sm = mock_managers["script"]
        mock_sm.get_metadata.side_effect = ValueError("Invalid JSON format")

        response = client.get('/scripts/corrupt_script')

        assert response.status_code == 400
        assert "Invalid JSON format" in str(response.data)

    def test_script_metadata_unexpected_error(self, client, mock_managers):
        """
        Tests fallback for unexpected errors.
        Covers the generic Exception path leading to a 500 InternalServerError.
        """
        mock_sm = mock_managers["script"]
        mock_sm.get_metadata.side_effect = Exception("Database connection lost")

        response = client.get('/scripts/error_script')

        assert response.status_code == 500
        assert "Database connection lost" in str(response.data)

    def test_script_metadata_empty_id_edge_case(self, client):
        """
        Tests the edge case of an empty script_id.
        Note: Flask routing usually handles this, but we test the internal check
        if the route allowed an empty string.
        """
        # In many Flask setups, client.get('/scripts/') might return 404 or 405 
        # based on trailing slashes, but if reached, the code raises BadRequest.
        response = client.get('/scripts/')
        
        # If the route matches but script_id is empty/missing
        assert response.status_code in [400, 404]
    
    # --- Tests for GET /layers/<layer_id>/tiles/<z>/<x>/<y>.png ---

    @patch('os.path.exists')
    @patch('App.app.send_file')
    def test_serve_tile_cache_hit(self, mock_send, mock_exists, client, mock_managers):
        """
        Tests the hot path where the tile already exists in the cache.
        Covers: Cache hit branch.
        """
        mock_fm = mock_managers["file"]
        mock_fm.raster_cache_dir = "/tmp/cache"
        mock_exists.return_value = True
        
        response = client.get('/layers/L1/tiles/1/2/3.png')
        
        # Verify it attempts to serve the specific cached file
        expected_cache_path = os.path.join("/tmp/cache", "L1_1_2_3.png")
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert args[0] == expected_cache_path
        assert kwargs['mimetype'] == "image/png"

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open')
    @patch('App.app.send_file')
    def test_serve_tile_outside_raster_bounds(self, mock_send, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests behavior when requested tile coordinates are outside the raster extent.
        Covers: width <= 0 or height <= 0 branch (Transparent tile generation).
        """
        mock_lm = mock_managers["layer"]
        mock_lm.export_raster_layer.return_value = "dummy.tif"
        # Mock bounds that result in invalid width/height
        mock_lm.tile_bounds.return_value = (0, 0, 10, 10)
        
        # Mock rasterio source context manager
        mock_src = MagicMock()
        mock_src.index.side_effect = [(0, 0), (-1, -1)] # row_stop < row_start
        mock_rasterio.return_value.__enter__.return_value = mock_src

        with patch('PIL.Image.Image.save') as mock_save:
            response = client.get('/layers/L1/tiles/10/1/1.png')
            assert response.status_code == 200
            # Verify a save happened (to cache and to BytesIO)
            assert mock_save.call_count >= 1

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open')
    @patch('numpy.dstack')
    def test_serve_tile_rgb_raster_success(self, mock_dstack, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests rendering a 3-band (RGB) raster tile.
        Covers: src.count >= 3 branch and coordinate index logic.
        """
        mock_lm = mock_managers["layer"]
        mock_lm.tile_bounds.return_value = (-9, 40, -8, 41)
        
        mock_src = MagicMock()
        mock_src.count = 3
        mock_src.index.side_effect = [(0, 0), (256, 256)] # width=256, height=256
        mock_src.read.return_value = np.zeros((3, 256, 256), dtype=np.uint8)
        mock_rasterio.return_value.__enter__.return_value = mock_src

        response = client.get('/layers/L1/tiles/5/10/10.png')
        
        assert response.status_code == 200
        mock_src.read.assert_called_once()
        # Verify cleaning was triggered
        mock_lm.clean_raster_cache.assert_called_once()

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open')
    def test_serve_tile_single_band_raster(self, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests rendering a single-band raster tile.
        Covers: src.count == 1 branch.
        """
        mock_src = MagicMock()
        mock_src.count = 1
        mock_src.index.side_effect = [(0, 0), (10, 10)]
        mock_src.read.return_value = np.zeros((1, 256, 256), dtype=np.uint8)
        mock_rasterio.return_value.__enter__.return_value = mock_src

        response = client.get('/layers/L1/tiles/1/0/0.png')
        assert response.status_code == 200

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open', side_effect=Exception("File Corrupt"))
    def test_serve_tile_general_exception(self, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests the high-level catch-all exception block.
        Covers: outer try-except Exception branch (raises ValueError).
        """
        response = client.get('/layers/L1/tiles/1/0/0.png')
        
        # The code raises ValueError, which usually results in 500 or 400 depending on app config
        assert response.status_code in [400, 500]
        assert b"Error serving tile" in response.data

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open')
    def test_serve_tile_read_window_exception(self, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests internal error handling when reading a specific window fails.
        Covers: inner try-except Exception branch (returns transparent tile).
        """
        mock_src = MagicMock()
        mock_src.index.return_value = (0, 10)
        mock_src.read.side_effect = Exception("Read error")
        mock_rasterio.return_value.__enter__.return_value = mock_src

        with patch('PIL.Image.new') as mock_new_img:
            client.get('/layers/L1/tiles/1/0/0.png')
            # Verify transparent image fallback was called
            mock_new_img.assert_called_with("RGBA", (256, 256), (0, 0, 0, 0))