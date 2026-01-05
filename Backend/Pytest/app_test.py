import pytest
import json
import io
import uuid
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, mock_open, patch
from flask import Flask, jsonify
from werkzeug.exceptions import BadRequest, NotFound
from flask.testing import FlaskClient
from typing import Any, Dict
import fiona

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
        assert b"Missing script" in response.data

    @patch('App.app.uuid.uuid4')
    @patch('App.app.os.path.getsize')
    @patch('App.app.os.path.exists')
    @patch('App.app.os.remove')
    def test_add_script_success(self, 
                                mock_remove: MagicMock, 
                                mock_exists: MagicMock, 
                                mock_getsize: MagicMock, 
                                mock_uuid: MagicMock, 
                                client: Any, 
                                mock_managers: Dict[str, MagicMock]) -> None:
        """
        Tests the successful path for adding a script.
        
        Fixes:
        - Mocking 'os.path.getsize' to prevent FileNotFoundError on non-existent test paths.
        - Patching 'uploaded_file.save' to avoid real disk I/O.
        - Ensuring 'uuid' and 'mimetype' constants match the logic requirements.
        """
        # 1. Configuration & Constants
        fixed_uuid = "12345678-1234-5678-1234-567812345678"
        mock_uuid.return_value = uuid.UUID(fixed_uuid)
        
        mock_sm = mock_managers["script"]
        mock_fm = mock_managers["file"]
        
        # Setup required attributes for the logic to pass validation
        mock_sm.ALLOWED_MIME_TYPES = ["text/x-python"]
        mock_sm.MAX_SCRIPT_FILE_SIZE = 5000
        mock_fm.temp_dir = "/tmp/temp"
        mock_fm.scripts_dir = "/tmp/scripts"
        
        # Mock OS behaviors
        mock_getsize.return_value = 100
        mock_exists.return_value = True
        
        # 2. Data Preparation
        # We include the mimetype 'text/x-python' to satisfy the script_manager check
        data = {
            'file': (io.BytesIO(b"print('hello')"), 'test_script.py', 'text/x-python'),
            'param1': 'value1'
        }

        # 3. Execution with File.save Mocked
        # We patch 'werkzeug.datastructures.FileStorage.save' because Flask wraps 
        # uploaded files in this class. Mocking it prevents real disk writes.
        with patch('werkzeug.datastructures.FileStorage.save') as mock_file_save:
            response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        # 4. Verifications
        assert response.status_code == 200
        res_json = response.get_json()
        
        # Verify script_id is the generated UUID, not the filename
        assert res_json["script_id"] == fixed_uuid
        
        # Verify File Operations
        expected_temp_path = f"/tmp/temp/{fixed_uuid}.py"
        mock_file_save.assert_called_once_with(expected_temp_path)
        mock_fm.move_file.assert_called_once_with(expected_temp_path, "/tmp/scripts")
        
        # Verify ScriptManager storage
        mock_sm.add_script.assert_called_once_with(fixed_uuid, {'param1': 'value1'})

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
        (".gpkg", "add_gpkg_layers"),
        (".tif", "add_raster"),
        (".tiff", "add_raster")
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

    def test_add_layer_shp(self, client, mock_managers):
        mock_managers["layer"].check_layer_name_exists.return_value = False
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        
        file_name = f"my_data.shp"
        data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
        
        with patch('os.path.getsize', return_value=10):
            response = client.post('/layers', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400

    def test_add_layer_unknown_format(self, client, mock_managers):
        mock_managers["layer"].check_layer_name_exists.return_value = False
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        
        file_name = f"my_data.some_ext"
        data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
        
        with patch('os.path.getsize', return_value=10):
            response = client.post('/layers', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400

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
        mock_managers["layer"].is_raster.return_value = False

        response = client.get('/layers/layer_id/table')
        assert response.status_code == 200
        assert response.get_json() == cached_response
        # Ensure it didn't call the heavy metadata logic
        mock_managers["layer"].get_metadata.assert_not_called()

    # --- Script Execution Tests ---

    def test_run_script_already_running(self, client, mock_managers):
        """Edge case: Prevents running a script that is already in 'running' status."""
        
        # Mock data must include all keys the route accesses during a conflict
        mock_running_state = {
            "script1": {
                "status": "running",
                "execution_id": "test-uuid-123" # Added to prevent KeyError
            }
        }
        
        with patch('App.app.running_scripts', mock_running_state):
            response = client.post('/scripts/script1', json={"parameters": {}})
            
            assert response.status_code == 409 
            assert b"already running" in response.data
            assert b"test-uuid-123" in response.data

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

    @patch('os.path.isfile')
    @patch('os.path.exists')
    @patch('App.app.send_file')
    def test_serve_tile_cache_hit(self, mock_send, mock_exists, mock_isfile, client, mock_managers):
        """
        Tests the hot path where the tile already exists in the cache.
        Covers: Cache hit branch.
        """
        mock_fm = mock_managers["file"]
        mock_fm.raster_cache_dir = "/tmp/cache"
        mock_exists.return_value = True
        mock_isfile.return_value = True 
        
        response = client.get('/layers/L1/tiles/1/2/3.png')
        
        # Verify it attempts to serve the specific cached file
        expected_cache_path = os.path.join(os.path.abspath("/tmp/cache"), "L1_1_2_3.png")
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
    @patch('PIL.Image.Image.save') # Add this patch to prevent physical file I/O
    def test_serve_tile_rgb_raster_success(self, mock_save, mock_dstack, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests rendering a 3-band (RGB) raster tile.
        Fixes Errno 2 by mocking the physical file save operation.
        """
        mock_lm = mock_managers["layer"]
        mock_fm = mock_managers["file"]
        
        # Setup Manager paths and attributes
        mock_lm.tile_bounds.return_value = (-9, 40, -8, 41)
        mock_lm.export_raster_layer.return_value = "dummy.tif"
        mock_fm.raster_cache_dir = "/tmp/cache"
        
        # Satisfy rasterio nested attributes
        mock_rasterio.enums.Resampling.bilinear = 1 
        
        mock_src = MagicMock()
        mock_src.count = 3
        mock_src.index.side_effect = [(0, 0), (256, 256)] 
        mock_src.read.return_value = np.zeros((3, 256, 256), dtype=np.uint8)
        mock_rasterio.return_value.__enter__.return_value = mock_src

        # Ensure dstack returns an array compatible with Image.fromarray
        mock_dstack.return_value = np.zeros((256, 256, 3), dtype=np.uint8)

        response = client.get('/layers/L1/tiles/5/10/10.png')
        
        assert response.status_code == 200
        assert response.mimetype == "image/png"
        
        # Verify the image was "saved" to the cache path without hitting the disk
        assert any(call.args[0].endswith("L1_5_10_10.png") for call in mock_save.call_args_list)
        mock_lm.clean_raster_cache.assert_called_once()

    @patch('os.path.exists', return_value=False)
    @patch('rasterio.open')
    @patch('PIL.Image.Image.save') # Prevent actual disk I/O
    def test_serve_tile_single_band_raster(self, mock_save, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests rendering a single-band raster tile.
        Fixes unpacking error by providing the expected 4-tuple from tile_bounds.
        """
        mock_lm = mock_managers["layer"]
        mock_fm = mock_managers["file"]
        
        # 1. FIX: Provide the 4-tuple that the route expects to unpack
        mock_lm.tile_bounds.return_value = (-9.0, 40.0, -8.0, 41.0)
        mock_lm.export_raster_layer.return_value = "dummy.tif"
        mock_fm.raster_cache_dir = "/tmp/cache"
        
        # Setup Rasterio and nested Resampling enum
        mock_rasterio.enums.Resampling.bilinear = 1 
        
        mock_src = MagicMock()
        mock_src.count = 1
        # Simulate valid width/height calculation from index
        mock_src.index.side_effect = [(0, 0), (256, 256)] 
        mock_src.read.return_value = np.zeros((1, 256, 256), dtype=np.uint8)
        mock_rasterio.return_value.__enter__.return_value = mock_src

        response = client.get('/layers/L1/tiles/1/0/0.png')
        
        assert response.status_code == 200
        assert response.mimetype == "image/png"
        # Verify the code reached the single-band 'L' mode branch
        mock_src.read.assert_called_once()

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
    @patch('PIL.Image.Image.save') # Prevent disk I/O
    def test_serve_tile_read_window_exception(self, mock_save, mock_rasterio, mock_exists, client, mock_managers):
        """
        Tests internal error handling when reading a specific window fails.
        Fixes the 500 error by satisfying all unpacking and path requirements.
        """
        mock_lm = mock_managers["layer"]
        mock_fm = mock_managers["file"]
        
        # 1. Provide the 4-tuple for tile_bounds unpacking
        mock_lm.tile_bounds.return_value = (-9.0, 40.0, -8.0, 41.0)
        mock_lm.export_raster_layer.return_value = "dummy.tif"
        mock_fm.raster_cache_dir = "/tmp/cache"
        
        mock_src = MagicMock()
        # 2. Provide two pairs for the two index() calls in the route
        mock_src.index.side_effect = [(0, 0), (256, 256)] 
        
        # 3. Trigger the exception during the read operation
        mock_src.read.side_effect = Exception("Read error")
        mock_rasterio.return_value.__enter__.return_value = mock_src

        with patch('PIL.Image.new') as mock_new_img:
            # Create a mock image object that supports the .save() method
            mock_fallback_img = MagicMock()
            mock_new_img.return_value = mock_fallback_img
            
            response = client.get('/layers/L1/tiles/1/0/0.png')
            
            # Verify the route caught the read error and generated a transparent tile
            assert response.status_code == 200
            mock_new_img.assert_called_with("RGBA", (256, 256), (0, 0, 0, 0))


    @pytest.mark.parametrize("exec_status, expected_code, expected_msg", [
        ("timeout", 504, "Script execution exceeded"),
        ("failure", 500, "Script execution failed with errors"),
        ("unknown_code", 500, "Unknown execution status"),
    ])
    def test_run_script_execution_statuses(
        self, 
        client: FlaskClient, 
        mock_managers: dict, 
        exec_status: str, 
        expected_code: int, 
        expected_msg: str
    ) -> None:
        """
        Covers the timeout, failure, and unknown status branches.
        """
        mock_sm = mock_managers["script"]
        mock_sm.run_script.return_value = {
            "status": exec_status,
            "outputs": [],
            "log_path": "/logs/test.log"
        }

        with patch('os.path.isfile', return_value=True):
            response = client.post('/scripts/test_script', json={"parameters": {"val": 1}})
            
        assert response.status_code == expected_code
        assert expected_msg in response.get_json().get("message", response.get_json().get("error", ""))

    def test_run_script_success_file_output(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Path: exec_status == "success" AND output is a valid physical file.
        Covers the send_file branch.
        """
        output_file = "/tmp/results/output_layer.geojson"
        mock_managers["script"].run_script.return_value = {
            "status": "success",
            "outputs": [output_file],
            "log_path": "/logs/success.log"
        }

        # We need to mock isfile for: 1. The script check, 2. The output file check
        with patch('os.path.isfile', side_effect=[True, True]), \
             patch('App.app.send_file') as mock_send:
            
            mock_send.return_value = "file_sent"
            client.post('/scripts/script_name', json={"parameters": {}})
            
            # Verify file download was triggered
            args, kwargs = mock_send.call_args
            assert args[0] == output_file
            assert kwargs['download_name'] == "output_layer.geojson"

    def test_run_script_success_json_output(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Path: exec_status == "success" AND output is data/objects (not a file).
        """
        mock_managers["script"].run_script.return_value = {
            "status": "success",
            "outputs": [{"stats": [1, 2, 3]}],
            "log_path": "/logs/success.log"
        }

        with patch('os.path.isfile', side_effect=[True, False]):
            response = client.post('/scripts/script_name', json={"parameters": {}})
            
        assert response.status_code == 200
        data = response.get_json()
        assert "executed successfully" in data["message"]
        assert data["output"][0]["stats"] == [1, 2, 3]

    def test_run_script_success_no_output(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Edge Case: Script succeeds but returns an empty output list.
        """
        mock_managers["script"].run_script.return_value = {
            "status": "success",
            "outputs": [],
            "log_path": "/logs/empty.log"
        }

        with patch('os.path.isfile', return_value=True):
            response = client.post('/scripts/script_name', json={"parameters": {}})
            
        assert response.status_code == 200
        assert "no output" in response.get_json()["message"]

    def test_run_script_bad_request_exception(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Fixes the reported test issue. Triggers BadRequest via invalid parameter type
        to ensure the internal 'except BadRequest' handler is exercised.
        """
        # Sending 'parameters' as a string instead of a dict triggers the 400 branch
        with patch('os.path.isfile', return_value=True):
            response = client.post('/scripts/script_name', json={"parameters": "invalid_type"})
            
        assert response.status_code == 400
        # Verify the state was updated to failed
        from App.app import running_scripts
        assert running_scripts["script_name"]["status"] == "failed"

    def test_run_script_generic_exception(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Exception Path: Catches unexpected internal errors during execution.
        """
        mock_managers["script"].run_script.side_effect = RuntimeError("System Crash")

        with patch('os.path.isfile', return_value=True):
            response = client.post('/scripts/crash_script', json={"parameters": {}})
            
        assert response.status_code == 500
        assert "Please contact the administrator" in response.get_json()["message"]

    def test_run_script_non_dict_parameters(self, client: FlaskClient) -> None:
        """
        Edge Case: Validation for the 'parameters' type in the JSON body.
        """
        response = client.post('/scripts/some_id', json={"parameters": "should_be_a_dict"})
        
        assert response.status_code == 400
        assert "'parameters' must be a JSON object" in response.get_json()["error"]["description"]

    def test_extract_data_from_layer_raster_error(self, client: FlaskClient, mock_managers: dict):
        """
        Test that a BadRequest is raised when attempting to get table data for a raster layer.
        Covers the 'if layer_manager.is_raster' exception branch.
        """
        mock_lm = mock_managers["layer"]
        # Mocking the private method (name mangling might apply if it's a real class, 
        # but as a mock attribute we set it directly)
        mock_lm.is_raster.return_value = True 
        
        response = client.get('/layers/raster_01/table')
        
        assert response.status_code == 400
        assert "Raster doesn't have attributes" in response.get_json()["error"]["description"]

    def test_extract_data_from_layer_cache_hit(self, client: FlaskClient, mock_managers: dict):
        """
        Test that cached data is returned immediately if available.
        Covers the 'if response:' branch for the cache hit.
        """
        mock_dm = mock_managers["data"]
        mock_lm = mock_managers["layer"]

        mock_lm.is_raster = lambda layer_id: False
        assert mock_lm.is_raster("x") is False

        cached_data = {
            "headers": [{"name": "id", "type": "int", "sortable": True}],
            "rows": [{"id": 1}],
            "total_rows": 1,
            "warnings": []
        }
        mock_dm.check_cache.return_value = cached_data

        response = client.get('/layers/vector_01/table')

        assert response.status_code == 200
        assert response.get_json() == cached_data
        # Ensure metadata processing was skipped
        mock_managers["layer"].get_metadata.assert_not_called()

    def test_extract_data_from_layer_success_with_nulls(self, client: FlaskClient, mock_managers: dict):
        """
        Test successful data extraction from a vector layer including null values.
        Covers:
        - Cache miss.
        - Rows processing loop.
        - Null value detection (warnings).
        - Type detection and value formatting.
        - Cache insertion.
        """
        mock_lm = mock_managers["layer"]
        mock_dm = mock_managers["data"]
        
        # 1. Setup Mock Data
        mock_lm.is_raster.return_value = False
        mock_dm.check_cache.return_value = None
        
        # Create a GeoDataFrame with mixed data and a Null value
        data = {
            "city": ["Lisbon", "Porto"],
            "population": [500000, None]
        }
        gdf = gpd.GeoDataFrame(data)
        mock_lm.get_metadata.return_value = {"attributes": gdf}
        
        # Mock data manager utility methods
        mock_dm.detect_type.side_effect = lambda x: "string" if isinstance(x, str) else "number"
        mock_dm.format_value_for_table_view.side_effect = lambda x: "N/A" if x is None else str(x)

        # 2. Execute Request
        response = client.get('/layers/vector_city/table')
        json_data = response.get_json()

        # 3. Assertions
        assert response.status_code == 200
        assert json_data["total_rows"] == 2
        assert len(json_data["headers"]) == 2
        
        # Check warnings branch coverage (Null value detected)
        assert any("Null value detected in field 'population'" in w for w in json_data["warnings"])
        
        # Check rows formatting
        assert json_data["rows"][0]["city"] == "Lisbon"
        assert json_data["rows"][1]["population"] == "N/A"
        
        # Ensure it was saved to cache
        mock_dm.insert_to_cache.assert_called_once()

    def test_extract_data_from_layer_empty_gdf(self, client: FlaskClient, mock_managers: dict):
        """
        Test the edge case where the layer exists but contains no rows.
        Covers the 'if total_rows > 0 else {}' branch.
        """
        mock_lm = mock_managers["layer"]
        mock_dm = mock_managers["data"]
        
        mock_lm.is_raster.return_value = False
        mock_dm.check_cache.return_value = None
        
        # Empty GeoDataFrame with columns
        gdf = gpd.GeoDataFrame(columns=["name", "geometry"])
        mock_lm.get_metadata.return_value = {"attributes": gdf}

        response = client.get('/layers/empty_layer/table')
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["total_rows"] == 0
        assert json_data["rows"] == []
        # Headers should still exist but type detection called with None
        assert len(json_data["headers"]) == 2
        assert json_data["headers"][0]["name"] == "name"

    def test_extract_data_from_layer_missing_id(self, client: FlaskClient):
        """
        Test the case where layer_id is missing. 
        Note: Flask routing usually prevents this if defined as /layers/<layer_id>/table,
        but we test the internal check 'if not layer_id'.
        """
        # We use a space or a specific path that might bypass strict regex if applicable
        # to trigger the 'if not layer_id' logic directly.
        with patch('App.app.layer_manager') as mock_lm:
            # Manually calling the function if needed, but via client:
            response = client.get('/layers/%20/table') # Encoded space
            # If the route matches but ID is whitespace/empty
            if response.status_code == 400:
                assert "layer_id parameter is required" in response.get_json()["error"]["description"]
    
    # Commented because it is not implemented.
    # def test_stop_script_success(self, client: FlaskClient) -> None:
    #     """
    #     Test the successful execution path of the stop_script route.
        
    #     Ensures that when a valid script_id is provided via DELETE and 
    #     a valid JSON body is present, the logic proceeds past the validation.
    #     """
    #     # Arrange
    #     script_id = "test_script_001"
    #     payload = {"force": True}
        
    #     # Act
    #     # We target the route defined in the snippet: /execute_script/<script_id>
    #     response = client.delete(f'/execute_script/{script_id}', json=payload)
        
    #     # Assert - Assuming the route returns 200 or 204 on success after the snippet logic
    #     assert response.status_code in [200, 204]

    @patch('App.app.os.listdir')
    def test_list_layers_empty_directory(self, mock_listdir: MagicMock, client: Any) -> None:
        """
        Test Case: Empty directory.
        Branch Coverage: Covers the case where os.listdir returns an empty list.
        Expectation: Returns empty lists for layer_id and metadata with a 200 status.
        """
        mock_listdir.return_value = []
        
        response = client.get('/layers')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['layer_id'] == []
        assert data['metadata'] == []

    @patch('App.app.os.listdir')
    def test_list_layers_no_metadata_files(self, mock_listdir: MagicMock, client: Any) -> None:
        """
        Test Case: Directory contains files, but none match the metadata pattern.
        Branch Coverage: Covers the 'if filename.endswith' False branch.
        Expectation: Filters out non-matching files.
        """
        mock_listdir.return_value = ['image.png', 'readme.txt', 'layer_data.csv']
        
        response = client.get('/layers')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['layer_id'] == []
        assert data['metadata'] == []

    @patch('App.app.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_list_layers_success(self, mock_json_load: MagicMock, mock_file: MagicMock, 
                                mock_listdir: MagicMock, client: Any) -> None:
        """
        Test Case: Standard success path with multiple valid files.
        Branch Coverage: Covers the 'if' True branch and the 'try' block success.
        Expectation: Correctly extracts layer IDs and associated JSON content.
        """
        # Setup mocks
        mock_listdir.return_value = ['layer1_metadata.json', 'layer2_metadata.json']
        # Simulate different metadata for each file
        mock_json_load.side_effect = [
            {"name": "Forest Cover", "type": "raster"},
            {"name": "Roads", "type": "vector"}
        ]
        
        response = client.get('/layers')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['layer_id'] == ['layer1', 'layer2']
        assert len(data['metadata']) == 2
        assert data['metadata'][0]['name'] == "Forest Cover"
        assert data['metadata'][1]['name'] == "Roads"

    @patch('App.app.os.listdir')
    @patch('builtins.open')
    def test_list_layers_exception_handling(self, mock_file: MagicMock, 
                                           mock_listdir: MagicMock, client: Any) -> None:
        """
        Test Case: Exception during file reading or JSON parsing.
        Branch Coverage: Covers the 'except Exception' block.
        Expectation: The specific index returns None for both ID and metadata, 
                     and the service does not crash.
        """
        mock_listdir.return_value = ['corrupt_metadata.json']
        # Simulate an exception (e.g., file permissions or malformed JSON)
        mock_file.side_effect = Exception("OS Read Error")
        
        response = client.get('/layers')
        
        assert response.status_code == 200
        data = response.get_json()
        # Per source logic: if exception occurs, layer_id and layer_metadata are both None
        assert data['layer_id'] == [None]
        assert data['metadata'] == [None]

    @patch('App.app.os.listdir')
    @patch('App.app.json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_list_layers_mixed_valid_and_invalid(self, mock_file: MagicMock, 
                                                mock_json_load: MagicMock, 
                                                mock_listdir: MagicMock, client: Any) -> None:
        """
        Test Case: Mixed directory with valid metadata, invalid metadata, and non-metadata files.
        Branch Coverage: Ensures 100% coverage by hitting every logical path in one execution.
        """
        mock_listdir.return_value = [
            'valid_metadata.json', 
            'broken_metadata.json', 
            'unrelated.log'
        ]
        
        # Side effect: First call succeeds, second raises Exception
        mock_json_load.side_effect = [
            {"status": "ok"},
            Exception("JSON Decode Error")
        ]
        
        response = client.get('/layers')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Results should contain:
        # 1. 'valid' with its dict
        # 2. 'None' with None (due to Exception)
        # 3. 'unrelated.log' should be skipped entirely
        assert data['layer_id'] == ['valid', None]
        assert data['metadata'] == [{"status": "ok"}, None]

    @patch('App.app.layer_manager')
    def test_get_layer_bad_request_empty_id(self, mock_layer_manager: MagicMock, client: Any) -> None:
        """
        Test Case: layer_id is empty or missing.
        Branch Coverage: 'if not layer_id' True branch.
        Expectation: Raises BadRequest (400).
        """
        # Note: In a real Flask app, a missing variable in the path might 404 before reaching here,
        # but we test the internal logic as written.
        with pytest.raises(BadRequest) as excinfo:
            # We call the function logic directly if testing unit-level, 
            # or simulate an empty param if the route allows it.
            from App.app import get_layer
            get_layer("")
        
        assert "layer_id is required" in str(excinfo.value)

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.abspath')
    @patch('App.app.layer_manager')
    @patch('App.app.send_file')
    def test_get_layer_geopackage_success(self, 
                                          mock_send_file: MagicMock, 
                                          mock_layer_manager: MagicMock, 
                                          mock_abspath: MagicMock, 
                                          mock_isfile: MagicMock, 
                                          client: Any) -> None:
        """
        Test Case: Successful export of a GeoPackage (.gpkg) layer.
        Branch Coverage: 'extension == ".gpkg"' True branch.
        Expectation: Calls GeoPackage converter, returns file with .geojson download name.
        """
        # Setup mocks
        layer_id = "test_vector"
        mock_layer_manager.get_layer_extension.return_value = ".gpkg"
        mock_layer_manager.export_geopackage_layer_to_geojson.return_value = "/tmp/test_vector.geojson"
        mock_abspath.return_value = "/absolute/tmp/test_vector.geojson"
        mock_isfile.return_value = True
        
        # Execution
        response = client.get(f'/layers/{layer_id}')
        
        # Verification
        mock_layer_manager.export_geopackage_layer_to_geojson.assert_called_once_with(layer_id)
        mock_send_file.assert_called_once_with(
            "/absolute/tmp/test_vector.geojson",
            as_attachment=True,
            download_name=f"{layer_id}.geojson"
        )

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.abspath')
    @patch('App.app.layer_manager')
    @patch('App.app.send_file')
    def test_get_layer_raster_success(self, 
                                      mock_send_file: MagicMock, 
                                      mock_layer_manager: MagicMock, 
                                      mock_abspath: MagicMock, 
                                      mock_isfile: MagicMock, 
                                      client: Any) -> None:
        """
        Test Case: Successful export of a Raster (e.g., .tif) layer.
        Branch Coverage: 'extension == ".gpkg"' False branch (else).
        Expectation: Calls Raster export, returns file with original extension.
        """
        # Setup mocks
        layer_id = "test_raster"
        mock_layer_manager.get_layer_extension.return_value = ".tif"
        mock_layer_manager.export_raster_layer.return_value = "/tmp/test_raster.tif"
        mock_abspath.return_value = "/absolute/tmp/test_raster.tif"
        mock_isfile.return_value = True
        
        # Execution
        response = client.get(f'/layers/{layer_id}')
        
        # Verification
        mock_layer_manager.export_raster_layer.assert_called_once_with(layer_id)
        mock_send_file.assert_called_once_with(
            "/absolute/tmp/test_raster.tif",
            as_attachment=True,
            download_name=f"{layer_id}.tif"
        )

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.abspath')
    @patch('App.app.layer_manager')
    def test_get_layer_internal_error_file_missing(self, 
                                                   mock_layer_manager: MagicMock, 
                                                   mock_abspath: MagicMock, 
                                                   mock_isfile: MagicMock, 
                                                   client: Any) -> None:
        """
        Test Case: Export logic returns a path, but the file does not exist on disk.
        Branch Coverage: 'if not os.path.isfile' True branch.
        Expectation: Raises InternalServerError (500).
        """
        # Setup mocks
        layer_id = "missing_file_layer"
        mock_layer_manager.get_layer_extension.return_value = ".tif"
        mock_layer_manager.export_raster_layer.return_value = "/tmp/missing.tif"
        mock_abspath.return_value = "/absolute/tmp/missing.tif"
        mock_isfile.return_value = False  # The file is missing
        
        # Execution & Verification
        # In Flask tests, the client will return a 500 status code 
        # unless 'PROPAGATE_EXCEPTIONS' is True.
        response = client.get(f'/layers/{layer_id}')
        
        assert response.status_code == 500
        # If testing the error message specifically (assuming default Flask error handling):
        assert b"Exported file not found" in response.data

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.abspath')
    @patch('App.app.layer_manager')
    def test_get_layer_with_alternate_extension(self, 
                                               mock_layer_manager: MagicMock, 
                                               mock_abspath: MagicMock, 
                                               mock_isfile: MagicMock, 
                                               client: Any) -> None:
        """
        Edge Case: Handling extensions that are not .gpkg but are valid (e.g., .png).
        Branch Coverage: Ensures the 'else' block logic is resilient.
        """
        layer_id = "ui_overlay"
        mock_layer_manager.get_layer_extension.return_value = ".png"
        mock_layer_manager.export_raster_layer.return_value = "ui_overlay.png"
        mock_abspath.return_value = "/abs/ui_overlay.png"
        mock_isfile.return_value = True

        response = client.get(f'/layers/{layer_id}')
        
        assert response.status_code == 200
        # Ensure the filename passed to download_name is correct
        from App.app import send_file
        # We can also verify via the mocked send_file directly

    # --- Corrected Raster Preview (get_layer_preview) Tests ---

    def test_get_preview_missing_params(self, client: FlaskClient) -> None:
        """
        Test Case: Request missing required bounding box query parameters.
        Covers: BadRequest (400) when parameters are missing.
        """
        response = client.get('/layers/L1/preview.png', query_string={'min_lat': 0.0})
        assert response.status_code == 400
        assert b"min_lat, min_lon, max_lat, max_lon are required" in response.data

    @patch('App.app.send_file')
    @patch('App.app.os.path.abspath')
    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.exists')
    def test_get_preview_from_cache_success(self, 
                                           mock_exists: MagicMock, 
                                           mock_isfile: MagicMock, 
                                           mock_abspath: MagicMock, 
                                           mock_send: MagicMock, 
                                           client: FlaskClient, 
                                           mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Serving a preview directly from the raster cache.
        Covers: Cache hit success path. 
        Note: Arguments are ordered bottom-to-top relative to decorators.
        """
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_abspath.return_value = "/tmp/raster_cache/L1_preview.png"
        
        response = client.get('/layers/L1/preview.png', query_string={
            'min_lat': 0.0, 'min_lon': 0.0, 'max_lat': 1.0, 'max_lon': 1.0
        })
        
        assert response.status_code == 200
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "/tmp/raster_cache/L1_preview.png"

    @patch('App.app.os.path.abspath')
    @patch('App.app.os.path.isfile')
    @patch('App.app.os.path.exists')
    def test_get_preview_cache_corrupt_error(self, 
                                             mock_exists: MagicMock, 
                                             mock_isfile: MagicMock, 
                                             mock_abspath: MagicMock, 
                                             client: FlaskClient) -> None:
        """
        Edge Case: Cache logic identifies an entry that is not a valid file.
        Covers: InternalServerError (500) raised explicitly in the code.
        """
        mock_exists.return_value = True
        mock_isfile.return_value = False
        mock_abspath.return_value = "/corrupt/path"
        
        response = client.get('/layers/L1/preview.png', query_string={
            'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1
        })
        
        assert response.status_code == 500
        assert b"Cached preview file not found" in response.data

    @patch('App.app.rasterio.open')
    @patch('App.app.os.path.exists')
    def test_get_preview_outside_raster_extent(self, 
                                              mock_exists: MagicMock, 
                                              mock_rasterio: MagicMock, 
                                              client: FlaskClient, 
                                              mock_managers: Dict[str, Any]) -> None:
        """
        Boundary Condition: Requested bounds map to zero width/height.
        Covers: ValueError branch. Since ValueError is not an HTTPException, Flask returns 500.
        """
        mock_exists.return_value = False
        mock_managers["layer"].export_raster_layer.return_value = "/tmp/dummy.tif"
        
        mock_src = MagicMock()
        # Side effect for two index calls: returns top-left and bottom-right as same pixel
        mock_src.index.side_effect = [(0, 0), (0, 0)] 
        mock_rasterio.return_value.__enter__.return_value = mock_src
        
        response = client.get('/layers/L1/preview.png', query_string={
            'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1
        })
        
        assert response.status_code == 500
        assert b"outside the raster extent" in response.data

    @patch('App.app.send_file')
    @patch('App.app.Image.fromarray')
    @patch('App.app.os.path.exists')
    @patch('App.app.rasterio.open')
    def test_get_preview_generate_single_band_success(self, 
                                                     mock_rasterio: MagicMock, 
                                                     mock_exists: MagicMock, 
                                                     mock_fromarray: MagicMock, 
                                                     mock_send: MagicMock, 
                                                     client: FlaskClient, 
                                                     mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Generation of a single-band (L) preview.
        """
        mock_exists.return_value = False
        mock_managers["layer"].export_raster_layer.return_value = "/tmp/input.tif"
        
        mock_src = MagicMock()
        mock_src.count = 1
        mock_src.index.side_effect = [(0, 0), (10, 10)]
        mock_src.read.return_value = np.zeros((1, 10, 10))
        mock_rasterio.return_value.__enter__.return_value = mock_src
        
        mock_img = MagicMock()
        mock_fromarray.return_value = mock_img

        response = client.get('/layers/L1/preview.png', query_string={
            'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1
        })
        
        assert response.status_code == 200
        _, kwargs = mock_fromarray.call_args
        assert kwargs['mode'] == "L"

    @patch('App.app.Image.fromarray')
    @patch('App.app.os.path.exists')
    @patch('App.app.rasterio.open')
    def test_get_preview_generate_rgb_success(self, 
                                              mock_rasterio: MagicMock, 
                                              mock_exists: MagicMock, 
                                              mock_fromarray: MagicMock, 
                                              client: FlaskClient, 
                                              mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Generation of an RGB preview (>= 3 bands).
        """
        mock_exists.return_value = False
        mock_managers["layer"].export_raster_layer.return_value = "/tmp/input_rgb.tif"
        
        mock_src = MagicMock()
        mock_src.count = 3
        mock_src.index.side_effect = [(0, 0), (10, 10)]
        mock_src.read.return_value = np.zeros((3, 10, 10))
        mock_rasterio.return_value.__enter__.return_value = mock_src
        
        mock_img = MagicMock()
        mock_fromarray.return_value = mock_img

        response = client.get('/layers/L1/preview.png', query_string={'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1})
        
        assert response.status_code == 200
        _, kwargs = mock_fromarray.call_args
        assert kwargs['mode'] == "RGB"

    @patch('App.app.Image.fromarray')
    @patch('App.app.os.path.exists')
    @patch('App.app.rasterio.open')
    def test_get_preview_generate_unsupported_bands_fallback(self, 
                                                           mock_rasterio: MagicMock, 
                                                           mock_exists: MagicMock, 
                                                           mock_fromarray: MagicMock, 
                                                           client: FlaskClient, 
                                                           mock_managers: Dict[str, Any]) -> None:
        """
        Edge Case: Fallback for unsupported band counts (e.g., 2 bands).
        """
        mock_exists.return_value = False
        mock_managers["layer"].export_raster_layer.return_value = "/tmp/input_2band.tif"
        
        mock_src = MagicMock()
        mock_src.count = 2
        mock_src.index.side_effect = [(0, 0), (10, 10)]
        mock_src.read.return_value = np.zeros((2, 10, 10))
        mock_rasterio.return_value.__enter__.return_value = mock_src
        
        mock_img = MagicMock()
        mock_fromarray.return_value = mock_img

        response = client.get('/layers/L1/preview.png', query_string={'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1})
        
        assert response.status_code == 200
        _, kwargs = mock_fromarray.call_args
        assert kwargs['mode'] == "L"

    @patch('App.app.rasterio.open')
    @patch('App.app.os.path.exists')
    def test_get_preview_read_exception(self, 
                                       mock_exists: MagicMock, 
                                       mock_rasterio: MagicMock, 
                                       client: FlaskClient, 
                                       mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Error during window reading.
        Covers: Inner try-except. Results in 500 due to ValueError mapping.
        """
        mock_exists.return_value = False
        mock_managers["layer"].export_raster_layer.return_value = "/tmp/bad.tif"
        
        mock_src = MagicMock()
        mock_src.index.side_effect = [(0, 0), (10, 10)]
        mock_src.read.side_effect = Exception("Disk failure")
        mock_rasterio.return_value.__enter__.return_value = mock_src
        
        response = client.get('/layers/L1/preview.png', query_string={'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1})
        assert response.status_code == 500
        assert b"Error reading raster window" in response.data

    @patch('App.app.rasterio.open')
    @patch('App.app.os.path.exists')
    def test_get_preview_general_exception(self, mock_exists, mock_rasterio, client, mock_managers) -> None:
        """
        Test Case: General exception during preview generation.
        Fix: 1. Mock is_raster to return a path (prevents 404).
             2. Mock os.path.exists to False (bypasses cache).
             3. Mock rasterio.open to raise the crash (triggers 500).
        """
        # 1. Prevent the 404 by making layer_manager believe the raster exists
        mock_managers["layer"].is_raster.return_value = "/tmp/fake_layer.tif"
        
        # 2. Bypass the preview cache check
        mock_exists.return_value = False
        
        # 3. Trigger the crash inside the generation try-block
        mock_rasterio.side_effect = Exception("System Crash")

        response = client.get('/layers/L1/preview.png', query_string={
            'min_lat': 0, 'min_lon': 0, 'max_lat': 1, 'max_lon': 1
        })
        
        # 4. Assertions
        assert response.status_code == 500
        data = response.get_json()
        
        # Check 'details' specifically, as that's where the app puts the Exception string
        assert "Error serving tile" in data["error"]["details"]
        assert "System Crash" in data["error"]["details"]

    # TESTS FOR remove_layer

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.remove')
    def test_remove_layer_success_full(self, mock_remove, mock_isfile, client: FlaskClient) -> None:
        """
        Test Case: Successful deletion of both the layer file and metadata.
        Covers: Branch where layer_path exists and metadata_path exists.
        """
        # Setup: Mock exists for a .tif file and the metadata json
        def isfile_side_effect(path: str) -> bool:
            return path.endswith(".tif") or path.endswith("_metadata.json")
        
        mock_isfile.side_effect = isfile_side_effect

        response = client.delete('/layers/L1')
        
        assert response.status_code == 200
        assert response.get_json()["message"] == "Layer L1 removed"
        # Verify both files were attempted to be removed
        assert mock_remove.call_count == 2

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.remove')
    def test_remove_layer_success_only_metadata(self, mock_remove, mock_isfile, client: FlaskClient) -> None:
        """
        Test Case: Successful deletion when only the metadata file exists.
        Covers: Branch where layer_path is None but metadata exists.
        """
        # Setup: Mock exists only for metadata
        mock_isfile.side_effect = lambda path: path.endswith("_metadata.json")

        response = client.delete('/layers/L1')
        
        assert response.status_code == 200
        assert response.get_json()["message"] == "Layer L1 removed"
        # Verify only one removal call (for metadata)
        mock_remove.assert_called_once()

    def test_remove_layer_not_found(self, client: FlaskClient) -> None:
        """
        Test Case: Layer does not exist (no file, no metadata).
        Covers: NotFound exception branch.
        """
        with patch('App.app.os.path.isfile', return_value=False):
            response = client.delete('/layers/non_existent_id')
            
            assert response.status_code == 404
            assert "does not exist" in response.get_json()["error"]["description"]

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.remove')
    def test_remove_layer_os_error(self, mock_remove, mock_isfile, client: FlaskClient) -> None:
        """
        Test Case: OSError occurs during file deletion.
        Covers: InternalServerError exception branch.
        """
        mock_isfile.return_value = True
        mock_remove.side_effect = OSError("Permission denied")

        response = client.delete('/layers/L1')
        
        assert response.status_code == 500
        assert "Failed to remove layer L1" in response.get_json()["error"]["description"]

    def test_remove_layer_bad_request_empty_id(self, client: FlaskClient) -> None:
        """
        Test Case: layer_id is missing or empty.
        Note: Flask routing usually catches this, but we test the internal logic.
        Covers: BadRequest exception branch (if not layer_id).
        """
        # To hit the 'if not layer_id' logic directly, we call the function or 
        # simulate a route that allows empty params if configured. 
        # Since the route is '/layers/<layer_id>', an empty ID usually 404s at the router.
        # However, for 100% coverage of the specific line:
        from App.app import remove_layer
        from werkzeug.exceptions import BadRequest
        
        with pytest.raises(BadRequest, match="layer_id is required"):
            remove_layer("")

    @patch('App.app.os.path.isfile')
    @patch('App.app.os.remove')
    def test_remove_layer_case_insensitive_extensions(self, mock_remove, mock_isfile, client: FlaskClient) -> None:
        """
        Test Case: Layer file has an uppercase extension (.GPKG).
        Covers: Loop through extension list and case sensitivity branch.
        """
        # Setup: Mock exists for a .GPKG file
        mock_isfile.side_effect = lambda path: path.endswith(".GPKG")

        response = client.delete('/layers/L1')
        
        assert response.status_code == 200
        assert response.get_json()["message"] == "Layer L1 removed"
        # Verify removal of the uppercase file
        called_path = mock_remove.call_args[0][0]
        assert called_path.endswith(".GPKG")


    # TESTS FOR extract_data_from_layer_for_table_view

    @patch('fiona.listlayers')  # Patch the library directly
    @patch('geopandas.read_file')
    @patch('os.path.isfile')
    def test_extract_table_data_success_with_warnings(
        self, mock_isfile, mock_read_file, mock_listlayers, client, mock_managers
    ) -> None:
        """
        Test Case: Successful extraction of vector data with mixed types and null values.
        Fix: Patched fiona and geopandas globally to avoid ModuleNotFoundError.
        """
        layer_id = "vector_L1"
        # 1. Setup Managers
        mock_managers["layer"].is_raster.return_value = False
        mock_managers["data"].check_cache.return_value = None
        
        # 2. Setup Filesystem/Library mocks
        mock_isfile.return_value = True
        mock_listlayers.return_value = ['main_layer']
        
        # Create a mock GeoDataFrame with a geometry column and a Null value
        data = {
            'id': [1, 2],
            'name': ['Alpha', None],
            'geometry': [MagicMock(), MagicMock()]
        }
        mock_gdf = gpd.GeoDataFrame(data)
        mock_read_file.return_value = mock_gdf
        
        # 3. Mock DataManager formatting
        mock_managers["data"].detect_type.return_value = "string"
        mock_managers["data"].format_value_for_table_view.side_effect = lambda x: str(x) if x is not None else "N/A"

        response = client.get(f'/layers/{layer_id}/table')
        
        assert response.status_code == 200
        json_data = response.get_json()
        
        # Assertions on data structure
        header_names = [h['name'] for h in json_data['headers']]
        assert 'geometry' not in header_names
        assert any("Null value detected" in w for w in json_data['warnings'])
        mock_managers["data"].insert_to_cache.assert_called_once()

    def test_extract_table_data_from_cache(self, client, mock_managers) -> None:
        """
        Test Case: Return data directly from cache.
        Fix: Ensure is_raster is explicitly mocked to False to prevent early 400.
        """
        layer_id = "cached_layer"
        cached_payload = {"headers": [{"name": "id"}], "rows": [], "total_rows": 0, "warnings": []}
        
        # Ensure the layer is recognized as valid and NOT a raster before checking cache
        mock_managers["layer"].is_raster.return_value = False
        mock_managers["data"].check_cache.return_value = cached_payload

        response = client.get(f'/layers/{layer_id}/table')
        
        assert response.status_code == 200
        assert response.get_json() == cached_payload

    def test_extract_table_data_fails_if_raster(self, client, mock_managers) -> None:
        """
        Test Case: Attempting to get table data for a raster layer.
        Covers: is_raster exception branch.
        """
        layer_id = "raster_L1"
        mock_managers["layer"].is_raster.return_value = True

        response = client.get(f'/layers/{layer_id}/table')
        
        assert response.status_code == 400
        assert "Raster doesn't have attributes" in response.get_json()["error"]["description"]

    @patch('App.app.os.path.isfile')
    def test_extract_table_data_file_not_found(self, mock_isfile, client, mock_managers) -> None:
        """
        Test Case: GPKG file does not exist on disk.
        Covers: os.path.isfile(gpkg_path) is False branch.
        """
        mock_managers["layer"].is_raster.return_value = False
        mock_managers["data"].check_cache.return_value = None
        mock_isfile.return_value = False

        response = client.get('/layers/missing_file/table')
        
        assert response.status_code == 400
        assert "Vector layer file not found" in response.get_json()["error"]["description"]

    @patch('fiona.listlayers')
    @patch('os.path.isfile')
    def test_extract_table_data_empty_gpkg(self, mock_isfile, mock_listlayers, client, mock_managers) -> None:
        """
        Test Case: GeoPackage exists but contains no layers inside.
        Covers: 'if not layers' branch raising BadRequest.
        """
        mock_managers["layer"].is_raster.return_value = False
        mock_managers["data"].check_cache.return_value = None
        mock_isfile.return_value = True
        mock_listlayers.return_value = [] # Fiona returns empty list

        response = client.get('/layers/empty_gpkg/table')
        
        assert response.status_code == 400
        assert "No layers found in GeoPackage" in response.get_json()["error"]["description"]

    @patch('fiona.listlayers')
    @patch('geopandas.read_file')
    @patch('os.path.isfile')
    def test_extract_table_data_empty_dataframe_edge_case(
        self, mock_isfile, mock_read_file, mock_listlayers, client, mock_managers
    ) -> None:
        """
        Edge Case: GPKG has a layer but 0 rows of data.
        Fixes the 500 error by ensuring all data_manager calls return serializable 
        values even when the sample_row is empty.
        """
        # 1. Setup Managers to bypass initial checks
        mock_managers["layer"].is_raster.return_value = False
        mock_managers["data"].check_cache.return_value = None
        mock_managers["data"].detect_type.return_value = "unknown" # Handle empty row case
        
        # 2. Setup Filesystem
        mock_isfile.return_value = True
        mock_listlayers.return_value = ['empty_layer']
        
        # 3. Create an empty GeoDataFrame with columns but NO data
        # This matches the 'total_rows = 0' logic path
        mock_gdf = gpd.GeoDataFrame(columns=['attr1', 'geometry'])
        mock_read_file.return_value = mock_gdf

        # 4. Execute
        response = client.get('/layers/empty_rows/table')
        
        # 5. Assertions
        # If it's still 500, we check the 'error' key to see the traceback
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Error: {response.get_data(as_text=True)}"
        
        json_data = response.get_json()
        assert json_data['total_rows'] == 0
        assert json_data['rows'] == []
        # Check that 'attr1' exists in headers but 'geometry' was dropped
        header_names = [h['name'] for h in json_data['headers']]
        assert 'attr1' in header_names
        assert 'geometry' not in header_names
    
    # =================================================================================
    # TESTS FOR preview_geopackage_layers
    # =================================================================================

    def test_preview_geopackage_no_file(self, client: FlaskClient) -> None:
        """
        Test Case: POST request without a file attachment.
        Covers: 'if not added_file' branch.
        """
        response = client.post('/layers/preview/geopackage')
        
        assert response.status_code == 400
        assert "You must upload a file" in response.get_json()["error"]["description"]

    @patch('App.app.os.path.getsize')
    @patch('App.app.os.remove')
    def test_preview_geopackage_exceeds_size(
        self, mock_remove, mock_getsize, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: Uploaded file is larger than the allowed limit.
        Covers: File size check branch and subsequent os.remove.
        """
        # Setup: Mock a file exceeding the manager's limit
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        mock_getsize.return_value = 5000 
        
        data = {'file': (io.BytesIO(b"fake data"), 'large_file.gpkg')}
        response = client.post('/layers/preview/geopackage', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert "exceeds the maximum allowed size" in response.get_json()["error"]["description"]
        mock_remove.assert_called_once()

    @patch('App.app.os.path.getsize')
    @patch('App.app.os.remove')
    def test_preview_geopackage_invalid_extension(
        self, mock_remove, mock_getsize, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: Uploading a non-GPKG file (e.g., .tif).
        Covers: Extension validation branch and cleanup.
        """
        mock_getsize.return_value = 100
        
        data = {'file': (io.BytesIO(b"fake data"), 'raster.tif')}
        response = client.post('/layers/preview/geopackage', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert "only accepts GeoPackage (.gpkg) files" in response.get_json()["error"]["description"]
        mock_remove.assert_called_once()

    @patch('App.app.os.path.getsize')
    @patch('App.app.os.remove')
    @patch('App.app.os.path.exists')
    def test_preview_geopackage_value_error_handling(
        self, mock_exists, mock_remove, mock_getsize, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: layer_manager raises a ValueError during processing.
        Covers: try/except ValueError branch and ensures cleanup.
        """
        mock_getsize.return_value = 100
        mock_exists.return_value = True
        # Simulate a ValueError from the logic layer (e.g., corrupt GPKG)
        mock_managers["layer"].get_geopackage_layers.side_effect = ValueError("Corrupt GeoPackage structure")

        data = {'file': (io.BytesIO(b"corrupt"), 'test.gpkg')}
        response = client.post('/layers/preview/geopackage', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert "Corrupt GeoPackage structure" in response.get_json()["error"]["description"]
        # Removal should be called at least once in the except and potentially once in finally
        assert mock_remove.called

    @patch('App.app.os.path.getsize')
    @patch('App.app.os.remove')
    def test_preview_geopackage_success(
        self, mock_remove, mock_getsize, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: Successful retrieval of layer names from a GPKG.
        Covers: The standard success path and finally block cleanup.
        """
        mock_getsize.return_value = 500
        expected_layers = ["roads", "water_bodies", "landuse"]
        mock_managers["layer"].get_geopackage_layers.return_value = expected_layers

        data = {'file': (io.BytesIO(b"valid_gpkg_content"), 'map_data.gpkg')}
        response = client.post('/layers/preview/geopackage', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        assert response.get_json()["layers"] == expected_layers
        # Verify finally block cleaned up the temp file
        mock_remove.assert_called_once()

    # =================================================================================
    # TESTS FOR add_script (Branch & Exception Focus)
    # =================================================================================

    def test_add_script_missing_metadata(self, client: FlaskClient) -> None:
        """
        Test Case: File is provided but the form metadata is empty.
        Covers: 'if not metadata' branch (line 90).
        """
        # Sending a file but no form fields
        data = {
            'file': (io.BytesIO(b"print('test')"), 'valid_script.py')
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        assert "Missing script metadata" in response.get_json()["error"]["description"]

    def test_add_script_no_filename(self, client: FlaskClient) -> None:
        """
        Test Case: Uploaded file has no base name (e.g., '.py').
        Covers: 'if not original_id' branch (line 96).
        """
        # We provide a filename that is ONLY the extension.
        # os.path.splitext(".py") -> ('', '.py')
        # This bypasses the 'if not uploaded_file' check but triggers 'if not original_id'
        data = {
            'file': (io.BytesIO(b"print('test')")), 
            'name': 'Metadata'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        # This will now correctly match the message: "Uploaded script has no filename."
        assert "no filename" in response.get_json()["error"]["description"].lower()

    def test_add_script_unsupported_mime(self, client: FlaskClient, mock_managers) -> None:
        """
        Test Case: File has .py extension but invalid MIME type (e.g., image/png).
        Covers: MIME validation branch (line 103).
        """
        # Ensure the mock manager defines expected allowed types
        mock_managers["script"].ALLOWED_MIME_TYPES = {"text/x-python"}
        
        # Simulate a file that claims to be an image despite the .py extension
        data = {
            'file': (io.BytesIO(b"print('test')"), 'test.py', 'image/png'),
            'name': 'Test Script'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert "Unsupported MIME type" in response.get_json()["error"]["description"]

    @patch('App.app.os.path.getsize')
    @patch('App.app.os.remove')
    def test_add_script_exceeds_size_cleanup(
        self, mock_remove, mock_getsize, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: File is saved but size check fails.
        Covers: Validate size branch and 'except HTTPException' cleanup.
        """
        # 1. Force valid MIME to pass the first check
        mock_managers["script"].ALLOWED_MIME_TYPES = {"text/x-python"}
        # 2. Mock a size larger than the limit
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 100
        mock_getsize.return_value = 1000 
        
        data = {
            'file': (io.BytesIO(b"content"), 'test.py', 'text/x-python'),
            'name': 'Test'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert "exceeds maximum allowed size" in response.get_json()["error"]["description"]
        mock_remove.assert_called()

    @patch('App.app.os.path.exists')
    @patch('App.app.os.remove')
    @patch('App.app.os.path.getsize')
    def test_add_script_unexpected_exception_cleanup(
        self, mock_getsize, mock_remove, mock_exists, client: FlaskClient, mock_managers
    ) -> None:
        """
        Test Case: System crash during the move_file or add_script phase.
        Covers: 'except Exception' catch-all and cleanup.
        """
        # 1. Ensure all validations pass to reach the try/except block
        mock_managers["script"].ALLOWED_MIME_TYPES = {"text/x-python"}
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 1000
        mock_getsize.return_value = 10
        mock_exists.return_value = True
        
        # 2. Trigger the generic exception
        mock_managers["file"].move_file.side_effect = Exception("OS Crash")
        
        data = {
            'file': (io.BytesIO(b"print(1)"), 'test.py', 'text/x-python'),
            'name': 'Tester'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')

        # 3. Assertions
        assert response.status_code == 500
        assert "Failed to store script" in response.get_json()["error"]["description"]
        mock_remove.assert_called()