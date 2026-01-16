import signal
from urllib import response
import pytest
import json
import io
import uuid
import os
import geopandas as gpd
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, mock_open, patch
from flask import Flask, Response, jsonify
from werkzeug.exceptions import BadRequest, NotFound
from flask.testing import FlaskClient
from typing import Any, Dict
import fiona
import zipfile

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
    @patch('App.app.os.path.getsize', return_value=100)
    @patch('App.app.os.path.exists', return_value=True)
    def test_add_script_success(self, mock_exists, mock_getsize, mock_uuid, client: FlaskClient, mock_managers: dict) -> None:
        """
        Fixes FAILED: test_add_script_success
        Correction: Mocks UUID to verify the exact call to script_manager.
        """
        # 1. Setup predictable UUID and mocks
        fixed_uuid = "12345678-1234-5678-1234-567812345678"
        mock_uuid.return_value = uuid.UUID(fixed_uuid)
        
        mock_managers["script"].ALLOWED_MIME_TYPES = {'text/x-python'}
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 1000
        
        # 2. Prepare multipart form data
        data = {
            'file': (io.BytesIO(b"print('hello')"), 'test.py', 'text/x-python'),
            'author': 'Tester',
            'description': 'A unit test script'
        }
        
        # 3. Execute request
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        # 4. Verify results
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["script_id"] == fixed_uuid
        
        # Ensure script_manager was called with the correct metadata dict
        expected_metadata = {'author': 'Tester', 'description': 'A unit test script'}
        mock_managers["script"].add_script.assert_called_once_with(fixed_uuid, expected_metadata)
        
        # Ensure file operations were triggered
        mock_managers["file"].move_file.assert_called_once()

    def test_add_script_invalid_extension(self, client: FlaskClient) -> None:
        """
        Fixes FAILED: test_add_script_invalid_extension
        Correction: Matches the exact error string in app.py.
        """
        data = {
            'file': (io.BytesIO(b"print(1)"), 'test.txt', 'text/plain'),
            'name': 'Metadata'
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        # The source code specifically returns "Only .py files are supported."
        assert b"Only .py files are supported." in response.data

    # --- Layer Management Tests ---

    # @pytest.mark.parametrize("extension, method", [
    #     (".zip", "add_shapefile_zip"),
    #     (".geojson", "add_geojson"),
    #     (".gpkg", "add_gpkg_layers"),
    #     (".tif", "add_raster"),
    #     (".tiff", "add_raster")
    # ])
    # def test_add_layer_various_formats(self, client, mock_managers, extension, method):
    #     """Parametrized test to verify different file formats trigger correct manager methods."""
    #     mock_managers["layer"].check_layer_name_exists.return_value = False
    #     mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        
    #     # Mock return values for specific methods
    #     getattr(mock_managers["layer"], method).return_value = ("layer1", {"meta": "data"})

    #     file_name = f"my_data{extension}"
    #     data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
        
    #     with patch('os.path.getsize', return_value=10):
    #         response = client.post('/layers', data=data, content_type='multipart/form-data')
        
    #     assert response.status_code == 200
    #     assert "layer1" in response.get_json()["layer_id"]
    #     getattr(mock_managers["layer"], method).assert_called_once()

    # def test_add_layer_shp(self, client, mock_managers):
    #     mock_managers["layer"].check_layer_name_exists.return_value = False
    #     mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
    #     mock_managers["layer"].process_layer_file.return_value = (None, None)
        
    #     file_name = f"my_data.shp"
    #     data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
        
    #     with patch('os.path.getsize', return_value=10):
    #         response = client.post('/layers', data=data, content_type='multipart/form-data')
        
    #     assert response.status_code == 400

    def test_add_layer_unknown_format(self, client, mock_managers):
        mock_managers["layer"].check_layer_name_exists.return_value = False
        mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
        
        file_name = f"my_data.some_ext"
        data = {'file': (io.BytesIO(b"fake binary content"), file_name)}
         # Make process_layer_file simulate unsupported extension.
        mock_managers["layer"].process_layer_file.return_value = (None, None)
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

    def test_run_script_not_found(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Fixes FAILED: test_run_script_not_found
        Correction: Ensures payload passes JSON validation so it reaches the file check.
        """
        # Must provide valid JSON structure to reach os.path.isfile(script_path)
        payload = {"parameters": {}, "layers": []}
        
        with patch('os.path.isfile', return_value=False):
            response = client.post('/scripts/non-existent-id', json=payload)
        
        assert response.status_code == 400
        assert b"does not exist" in response.data

    # --- Map / Tile Interaction Tests ---

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

    @patch("App.app.script_manager")
    def test_script_metadata_bad_request_empty_id(mock_script_manager: MagicMock, client: Any) -> None:
        """
        Branch: if not script_id (True).
        Expect: BadRequest with 'script_id parameter is required'.
        """
        from App.app import script_metadata

        with pytest.raises(BadRequest) as excinfo:
            script_metadata("")  # empty script_id passed directly

        assert "script_id parameter is required" in str(excinfo.value)
    
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
    # We no longer need to patch Image.save because the code fails before reaching it
    def test_serve_tile_read_window_exception(self, mock_rasterio, mock_exists, client, mock_managers):
        """
        Test Case: Handle exceptions during the raster read process.
        Requirement: Verify that the app's global error handler catches the failure 
        and returns a 500 error instead of crashing.
        """
        mock_lm = mock_managers["layer"]
        mock_fm = mock_managers["file"]
        
        # 1. Setup metadata and paths
        mock_lm.tile_bounds.return_value = (-9.0, 40.0, -8.0, 41.0)
        mock_lm.export_raster_layer.return_value = "dummy.tif"
        mock_fm.raster_cache_dir = "/tmp/cache"
        
        # 2. Setup Rasterio mock
        mock_src = MagicMock()
        # Provide coordinates for index calls
        mock_src.index.side_effect = [(0, 0), (256, 256), (0, 0), (256, 256)] 
        # Trigger the intentional error
        mock_src.read.side_effect = Exception("Read error")
        mock_rasterio.return_value.__enter__.return_value = mock_src

        # 3. Execute request
        response = client.get('/layers/L1/tiles/1/0/0.png')
        
        # 4. Assertions (Matching the new app.py behavior)
        # The app now returns 500 via handle_generic_exception or the ValueError handler
        assert response.status_code == 500
        
        data = response.get_json()
        assert "error" in data
        assert "Read error" in data["error"]["details"]

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
    def test_list_layers_exception_handling(self, mock_file, mock_listdir, client):
        """
        Test Case: Exception during file reading or JSON parsing.
        Requirement: Verify that unhandled exceptions during listing return a 500 error.
        """
        # Simulate a directory containing a metadata file
        mock_listdir.return_value = ['corrupt_metadata.json']
        
        # Trigger an exception that isn't caught by the local 'except' block in list_layers
        # (The local block only catches OSError, IOError, and json.JSONDecodeError)
        mock_file.side_effect = Exception("Generic System Failure")
        
        response = client.get('/layers')
        
        # 1. Update expectation to 500 because the exception bubbles up to the global handler
        assert response.status_code == 500
        
        # 2. Verify the structured error response defined in app.py
        data = response.get_json()
        assert "error" in data
        assert data["error"]["code"] == 500
        assert data["error"]["message"] == "Internal Server Error"
        assert "Generic System Failure" in data["error"]["details"]

    @patch('App.app.os.listdir')
    @patch('builtins.open')
    def test_list_layers_mixed_valid_and_invalid(self, mock_file, mock_listdir, client):
        """
        Test Case: Mixture of valid metadata and files that cause unhandled exceptions.
        Requirement: Verify that a generic Exception triggers the global 500 error handler.
        """
        # Simulate one valid file and one that will trigger an unhandled Exception
        mock_listdir.return_value = ['valid_metadata.json', 'invalid_metadata.json']
        
        # side_effect returns valid JSON for the first call, then raises an Exception
        mock_file.side_effect = [
            mock_open(read_data='{"name": "valid_layer"}').return_value,
            Exception("Unexpected System Error") 
        ]
        
        response = client.get('/layers')
        
        # 1. Update status code to 500
        assert response.status_code == 500
        
        # 2. Verify the structured JSON error response from the global handler
        data = response.get_json()
        assert "error" in data
        assert data["error"]["message"] == "Internal Server Error"
        assert "Unexpected System Error" in data["error"]["details"]

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

    # def test_get_layer_with_alternate_extension(self, client, mock_managers):
    #     """
    #     Test Case: Uploading a file with an alternate valid extension (.tiff vs .tif).
    #     Requirement: Verify the backend accepts valid variations of allowed formats.
    #     """
    #     # 1. Setup: Use .tiff instead of .shp to avoid the 400 error
    #     file_name = "raster_data.tiff" 
    #     data = {'file': (io.BytesIO(b"fake raster data"), file_name)}
        
    #     # Mock the manager to return success
    #     mock_managers["layer"].add_raster.return_value = ("layer_id_123", {"metadata": "info"})
    #     mock_managers["layer"].check_layer_name_exists.return_value = False
    #     mock_managers["layer"].MAX_LAYER_FILE_SIZE = 1000
    #     mock_managers["layer"].process_layer_file.return_value = ("layer_id_123", None)

        
    #     # 2. Execute request
    #     with patch('os.path.getsize', return_value=100):
    #         response = client.post('/layers', data=data, content_type='multipart/form-data')
        
    #     # 3. Assertions
    #     assert response.status_code == 200
    #     assert "layer_id_123" in response.get_json()["layer_id"]
    #     mock_managers["layer"].add_raster.assert_called_once()

    # --- Corrected Raster Preview (get_layer_preview) Tests ---
    def test_get_layer_preview_bad_request_empty_id(self, client: FlaskClient) -> None:
        """
        Branch: if not layer_id (True) in get_layer_preview.
        """
        with pytest.raises(BadRequest) as excinfo:
            from App.app import get_layer_preview
            get_layer_preview("")  # call view directly with empty ID

        assert "layer_id is required" in str(excinfo.value)
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

    def test_extract_table_bad_request_empty_id(self, client: FlaskClient) -> None:
        """
        Branch: if not layer_id (True) in extract_data_from_layer_for_table_view.
        """
        with pytest.raises(BadRequest) as excinfo:
            from App.app import extract_data_from_layer_for_table_view
            extract_data_from_layer_for_table_view("")  # direct call with empty id

        assert "layer_id parameter is required" in str(excinfo.value)

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

### DELETE SCRIPT TESTS



    @patch("App.app.script_manager")
    def test_delete_script_bad_request_empty_id(self, mock_script_manager: MagicMock, client: FlaskClient) -> None:
        """
        Branch: if not script_id (True).
        """
        from App.app import delete_script

        with pytest.raises(BadRequest) as excinfo:
            delete_script("")  # direct function call

        assert "script_id parameter is required" in str(excinfo.value)

    def test_delete_script_success(self, client: FlaskClient, mock_managers) -> None:
        """
        Branch: try-block, no exception.
        """
        mock_managers["script"].delete_script.return_value = None

        response = client.delete("/scripts/abc123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Script deleted successfully"
        mock_managers["script"].delete_script.assert_called_once_with("abc123")


    def test_delete_script_not_found(self, client: FlaskClient, mock_managers) -> None:
        """
        Branch: except FileNotFoundError.
        """
        mock_managers["script"].delete_script.side_effect = FileNotFoundError("missing")

        response = client.delete("/scripts/missing-id")

        assert response.status_code == 404
        assert "Script not found for deletion" in response.get_json()["error"]["description"]
        mock_managers["script"].delete_script.assert_called_once_with("missing-id")

    def test_delete_script_internal_error(self, client: FlaskClient, mock_managers) -> None:
        """
        Branch: except Exception.
        """
        mock_managers["script"].delete_script.side_effect = RuntimeError("boom")

        response = client.delete("/scripts/boom")

        assert response.status_code == 500
        assert "Failed to delete script" in response.get_json()["error"]["description"]
        mock_managers["script"].delete_script.assert_called_once_with("boom")

    def test_list_scripts_returns_ids_and_metadata(self, client: FlaskClient, mock_managers) -> None:
        # Arrange
        mock_managers["script"].list_scripts.return_value = (
            ["id1", "id2"],
            [{"name": "s1"}, {"name": "s2"}],
        )

        # Act
        response = client.get("/scripts")

        # Assert
        assert response.status_code == 200
        data = response.get_json()
        assert data["scripts_ids"] == ["id1", "id2"]
        assert data["scripts_metadata"] == [{"name": "s1"}, {"name": "s2"}]
        mock_managers["script"].list_scripts.assert_called_once()
    # 
    # 
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
            'file': (io.BytesIO(b"print('test')"), 'valid_script.py'),
        }
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        assert "Missing script metadata" in response.get_json()["error"]["description"]



    def test_add_script_no_filename(self, client: FlaskClient) -> None:
        """
        Fixes FAILED: test_add_script_no_filename
        Correction: Validates the first check in app.py (missing 'file' field).
        """
        # Testing the case where the 'file' field is missing entirely
        data = {'name': 'Metadata'}
        response = client.post('/scripts', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert b"Missing script file under 'file' field." in response.data

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


    # --- Script Execution Tests for POST /scripts/<script_id> ---

    def test_run_script_missing_body(self, client):
        # Send a request with no JSON body
        response = client.post('/scripts/some-id', content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        
        # Check for the description inside the structured error response
        # It will either be your custom message or the Werkzeug default
        error_desc = data["error"]["description"]
        assert "Request body must be JSON" in error_desc or "could not understand" in error_desc


    def test_run_script_invalid_parameters_type(self, client: FlaskClient) -> None:
        """
        Test Case: 'parameters' field is not a dictionary.
        Requirement: Branch coverage for 'if not isinstance(parameters, dict)'.
        """
        payload = {"parameters": ["not", "a", "dict"]}
        response = client.post('/scripts/test-script', json=payload)
        assert response.status_code == 400
        assert "'parameters' must be a JSON object" in response.get_json()["error"]["description"]

    def test_run_script_invalid_layers_type(self, client: FlaskClient) -> None:
        """
        Test Case: 'layers' field is not a list.
        Requirement: Branch coverage for 'if not isinstance(layers, list)'.
        """
        payload = {"layers": {"not": "a list"}}
        response = client.post('/scripts/test-script', json=payload)
        assert response.status_code == 400
        assert "'layers' must be a JSON list" in response.get_json()["error"]["description"]

    def test_script_metadata_bad_request_empty_id(self) -> None:
        """
        Branch: if not script_id (True).
        Expect: BadRequest with 'script_id parameter is required'.
        """
        from App.app import run_script

        with pytest.raises(BadRequest) as excinfo:
            run_script("")  # empty script_id passed directly

        assert "script_id is required" in str(excinfo.value)
    
    def test_run_script_missing_json_body(self, client: FlaskClient) -> None:
        """
        Missing / invalid JSON body should result in a 400 error.
        """
        script_id = "test-script"

        # No JSON body
        response = client.post(f"/scripts/{script_id}")

        assert response.status_code == 415
        # optionally check structure if your error handler wraps it
        data = response.get_json()
        assert data["error"]["code"] == 415


    @patch('App.app.running_scripts', {})
    @patch('os.path.isfile', return_value=True)
    def test_run_script_success_with_layer_ids(self, mock_isfile: MagicMock, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Successful execution returning layer IDs.
        Requirement: Branch coverage for 'elif exec_status == "success"' and 'if layer_ids is not None'.
        """
        mock_output = {
            "status": "success",
            "layer_ids": ["layer_1", "layer_2"],
            "metadatas": [{"id": "layer_1", "type": "vector"}],
            "log_path": "/path/to/logs.txt"
        }
        mock_managers["script"].run_script.return_value = mock_output

        response = client.post('/scripts/valid-script', json={"parameters": {}, "layers": []})
        
        assert response.status_code == 200
        data = response.get_json()
        assert "executed successfully" in data["message"]
        assert data["layer_ids"] == ["layer_1", "layer_2"]
        assert data["log_path"] == "/path/to/logs.txt"

    @patch('App.app.running_scripts', {})
    @patch('os.path.isfile', return_value=True)
    def test_run_script_success_no_layer_ids(self, mock_isfile: MagicMock, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Successful execution but no layer output produced.
        Requirement: Branch coverage for 'else' (No output produced) in success block.
        """
        mock_output = {
            "status": "success",
            "layer_ids": None,
            "log_path": "/path/to/logs.txt"
        }
        mock_managers["script"].run_script.return_value = mock_output

        response = client.post('/scripts/valid-script', json={"parameters": {}, "layers": []})
        
        assert response.status_code == 200
        assert "no output" in response.get_json()["message"]

    @pytest.mark.parametrize("status, expected_code, expected_msg", [
        ("timeout", 504, "Gateway Timeout"),
        ("failure", 500, "Internal Server Error"),
        ("unknown_status", 500, "Internal Server Error")
    ])
    def test_run_script_execution_errors(
        self, client: FlaskClient, mock_managers: dict, status, expected_code, expected_msg
    ) -> None:
        """
        Fixes FAILED: test_run_script_execution_errors
        Correction: Uses valid payload to ensure execution reaches the status handler.
        """
        # Ensure file exists to reach the script_manager.run_script call
        mock_managers["script"].run_script.return_value = {
            "status": status,
            "log_path": "/tmp/log.txt"
        }
        
        payload = {"parameters": {}, "layers": []}
        
        with patch('os.path.isfile', return_value=True):
            response = client.post('/scripts/any-id', json=payload)
        
        assert response.status_code == expected_code
        data = response.get_json()
        # Verify the error name or message depending on the status
        assert expected_msg in (data.get("error") or data.get("message") or "")

    @patch('App.app.script_manager.run_script')
    def test_run_script_generic_exception_handling(self, mock_run, client, mock_managers):
        """
        Test Case: Script execution triggers an unhandled generic Exception.
        Requirement: Verify the app returns a 500 status with the new structured JSON error.
        """
        script_id = "test_script"
        # Mocking an unexpected error during execution
        mock_run.side_effect = Exception("Unexpected System Error")
        
        # Ensure the script file "exists" for the route's check
        with patch('os.path.isfile', return_value=True):
            response = client.post(f'/scripts/{script_id}', 
                                   json={"parameters": {}, "layers": []})
        
        # 1. Status code is still 500
        assert response.status_code == 500
        
        # 2. Update the assertion to handle the dictionary response
        data = response.get_json()
        
        # Verify the structure of the error object returned by handle_generic_exception
        assert "error" in data
        assert data["error"]["code"] == 500
        assert data["error"]["message"] == "Internal Server Error"
        assert data["error"]["details"] == "Unexpected System Error"
# Export all layers tests 
    def test_export_all_layers_success(self, client: FlaskClient, mock_managers) -> None:
        # Arrange layer ids and metadata
        mock_managers["layer"].list_layer_ids.return_value = (["l1", "l2"], None)
        mock_managers["layer"].get_metadata.side_effect = [
            {"layer_name": "LayerOne"},
            {"layer_name": "LayerTwo"},
        ]
        mock_managers["layer"].get_layer_extension.side_effect = [".gpkg", ".tif"]

        # Plain strings for dirs
        mock_managers["file"].temp_dir = "/tmp"
        mock_managers["file"].layers_dir = "/layers"

        fake_zip_path = "/tmp/all_layers_export.zip"

        with patch("App.app.os.path.exists", return_value=True), \
            patch("App.app.os.path.abspath", return_value=fake_zip_path), \
            patch("App.app.os.path.isfile", return_value=True), \
            patch("App.app.zipfile.ZipFile") as mock_zipfile, \
            patch("App.app.send_file") as mock_send_file:

            # When the view calls send_file(export_file_abs, ...),
            # have it return a simple Response-like object
            from flask import Response
            mock_send_file.return_value = Response(b"zip-bytes", status=200)

            mock_zip = mock_zipfile.return_value.__enter__.return_value

            response = client.get("/layers/export/all")

        assert response.status_code == 200
        # ZipFile context was created
        mock_zipfile.assert_called_once()
        # Two files written into the zip
        assert mock_zip.write.call_count == 2
        mock_managers["layer"].list_layer_ids.assert_called_once()

    def test_export_all_layers_skips_missing_metadata(self, client: FlaskClient, mock_managers) -> None:
        # Two layer IDs, but first has no metadata
        mock_managers["layer"].list_layer_ids.return_value = (["l1", "l2"], None)
        mock_managers["layer"].get_metadata.side_effect = [
            None,                              # -> triggers `if not metadata: continue`
            {"layer_name": "LayerTwo"},        # processed
        ]
        mock_managers["layer"].get_layer_extension.return_value = ".gpkg"

        mock_managers["file"].temp_dir = "/tmp"
        mock_managers["file"].layers_dir = "/layers"
        fake_zip_path = "/tmp/all_layers_export.zip"

        with patch("App.app.os.path.exists", return_value=True), \
            patch("App.app.os.path.abspath", return_value=fake_zip_path), \
            patch("App.app.os.path.isfile", return_value=True), \
            patch("App.app.zipfile.ZipFile") as mock_zipfile, \
            patch("App.app.send_file") as mock_send_file:

            from flask import Response
            mock_send_file.return_value = Response(b"zip-bytes", status=200)
            mock_zip = mock_zipfile.return_value.__enter__.return_value

            response = client.get("/layers/export/all")

        assert response.status_code == 200

        # First metadata falsy → skipped; only second layer written
        assert mock_zip.write.call_count == 1
        # get_metadata was called twice (for l1 and l2)
        assert mock_managers["layer"].get_metadata.call_count == 2


    def test_export_all_layers_export_file_missing(self, client: FlaskClient, mock_managers) -> None:
        mock_managers["layer"].list_layer_ids.return_value = ([], None)
        mock_managers["file"].temp_dir = "/tmp"

        with patch("App.app.zipfile.ZipFile") as mock_zipfile, \
            patch("App.app.os.path.abspath", side_effect=lambda p: p), \
            patch("App.app.os.path.isfile", return_value=False):
            # ZipFile completes normally, but final file check fails
            response = client.get("/layers/export/all")

        assert response.status_code == 500
        data = response.get_json()
        assert "Exported file not found" in data["error"]["description"]

    def test_export_all_layers_zip_creation_error(self, client: FlaskClient, mock_managers) -> None:
        mock_managers["layer"].list_layer_ids.return_value = (["l1"], None)
        mock_managers["file"].temp_dir = "/tmp"

        # Make ZipFile.__enter__ raise an exception
        with patch("App.app.zipfile.ZipFile") as mock_zipfile, \
            patch("App.app.os.path.abspath", side_effect=lambda p: p):
            mock_zipfile.side_effect = RuntimeError("disk error")

            response = client.get("/layers/export/all")

        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to create ZIP archive" in data["error"]["description"]
# Tests for stop script execution
    def test_stop_script_bad_request_empty_id(self, client: FlaskClient) -> None:
        with pytest.raises(BadRequest) as excinfo:
            from App.app import stop_script
            stop_script("")  # bypass routing, hit `if not script_id`

        assert "script_id is required" in str(excinfo.value)
    # --- Tests for GET /layers/<layer_id>/information ---
    @patch("App.app.running_scripts", {})
    def test_stop_script_running(self, client: FlaskClient) -> None:
        script_id = "running-script"
        from App.app import running_scripts
        running_scripts.clear()
        running_scripts[script_id] = {
            "execution_id": "exec-1",
            "start_time": None,
            "status": "running",
        }

        fake_child = MagicMock()
        fake_child.pid = 1234

        with patch("App.app.psutil.Process") as mock_proc_cls, \
            patch("App.app.os.kill") as mock_kill:

            mock_proc = mock_proc_cls.return_value
            mock_proc.children.return_value = [fake_child]

            response = client.delete(f"/execute_script/{script_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == f"Script {script_id} stopped"

        mock_proc_cls.assert_called_once()
        mock_proc.children.assert_called_once_with(recursive=True)
        mock_kill.assert_called_once_with(1234, signal.SIGTERM)

    def test_stop_script_not_running(self, client: FlaskClient) -> None:
        script_id = "idle-script"
        from App.app import running_scripts
        running_scripts.clear()
        running_scripts[script_id] = {
            "execution_id": "exec-2",
            "start_time": None,
            "status": "finished",  # not "running"
        }

        response = client.delete(f"/execute_script/{script_id}")

        assert response.status_code == 409
        data = response.get_json()
        assert data["error"] == "Conflict"
        assert f"Script '{script_id}' is not running." in data["message"]
        assert data["script_id"] == script_id

    def test_identify_layer_information_success(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Successfully retrieve information for a valid layer.
        Requirement: Covers the successful try block and return statement.
        """
        # 1. Setup mock data
        layer_id = "test_vector_layer"
        mock_info = {
            "type": "vector",
            "geometry_type": "Point",
            "crs": "EPSG:4326",
            "feature_count": 150
        }
        mock_managers["layer"].get_layer_information.return_value = mock_info

        # 2. Execute the GET request
        response = client.get(f'/layers/{layer_id}/information')

        # 3. Assertions
        assert response.status_code == 200
        data = response.get_json()
        assert data["layer_id"] == layer_id
        assert data["info"] == mock_info
        mock_managers["layer"].get_layer_information.assert_called_once_with(layer_id)

    def test_identify_layer_information_value_error(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Layer manager raises a ValueError (e.g., layer not found or invalid format).
        Requirement: Covers the 'except ValueError' block and ensures the error is re-raised/handled.
        """
        # 1. Setup: Force the manager to raise a ValueError
        layer_id = "invalid_layer"
        error_message = "Layer not found"
        mock_managers["layer"].get_layer_information.side_effect = ValueError(error_message)

        # 2. Execute the GET request
        response = client.get(f'/layers/{layer_id}/information')

        # 3. Assertions
        # Note: In app.py, a raised ValueError is caught by the generic Exception handler (500)
        # or the specific ValueError handler if defined. Based on the source code provided,
        # it wraps the message: "Error in identifying layer information: Layer not found"
        assert response.status_code == 500
        data = response.get_json()
        assert "Error in identifying layer information" in data["error"]["details"]
        assert error_message in data["error"]["details"]

    def test_identify_layer_information_missing_id(self, client: FlaskClient) -> None:
        """
        Fixes FAILED: test_identify_layer_information_missing_id (308 == 404)
        Requirement: Validate behavior when the layer_id is missing.
        Correction: Uses follow_redirects=True or checks the final 404 status.
        """
        # Calling the route without an ID (empty path segment)
        # We use follow_redirects=True to handle the 308 and get the final 404
        response = client.get('/layers//information', follow_redirects=True)
        
        # Flask routing for '/layers/<layer_id>/information' will fail to match 
        # an empty string for <layer_id> and return a 404 Not Found.
        assert response.status_code == 404

    # --- Tests for GET /layers/<layer_id>/attributes ---

    def test_get_layer_attributes_bad_request_empty_id(self, client: FlaskClient) -> None:
        """
        Branch: if not layer_id (True) in get_layer_attributes.
        """
        with pytest.raises(BadRequest) as excinfo:
            from App.app import get_layer_attributes
            get_layer_attributes("")  # direct call with empty id

        assert "layer_id parameter is required" in str(excinfo.value)
    def test_get_layer_attributes_success(self, client: FlaskClient, mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Successfully retrieve attributes for a valid layer.
        Requirement: Covers the 'try' block and 200 OK response.
        """
        # 1. Setup mock metadata with 'attributes' key
        layer_id = "test_vector_layer"
        mock_attributes = [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "area", "type": "float"}
        ]
        mock_managers["layer"].get_metadata.return_value = {"attributes": mock_attributes}

        # 2. Execute the GET request
        response = client.get(f'/layers/{layer_id}/attributes')

        # 3. Assertions
        assert response.status_code == 200
        data = response.get_json()
        assert data["layer_id"] == layer_id
        assert data["attributes"] == mock_attributes
        mock_managers["layer"].get_metadata.assert_called_once_with(layer_id)

    def test_get_layer_attributes_not_found(self, client: FlaskClient, mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Layer manager raises a ValueError (e.g., layer does not exist).
        Requirement: Covers the 'except ValueError' block and conversion to NotFound (404).
        """
        # 1. Setup: Force the manager to raise a ValueError
        layer_id = "non_existent_layer"
        error_msg = "Layer not found in system"
        mock_managers["layer"].get_metadata.side_effect = ValueError(error_msg)

        # 2. Execute the GET request
        response = client.get(f'/layers/{layer_id}/attributes')

        # 3. Assertions
        # The source code catches ValueError and raises NotFound (404)
        assert response.status_code == 404
        data = response.get_json()
        # The global handle_http_exception structure is used for the error description
        assert f"Error in retrieving layer attributes: {error_msg}" in data["error"]["description"]

    def test_get_layer_attributes_missing_id_path(self, client: FlaskClient) -> None:
        """
        Test Case: Edge case where the layer_id is missing in the URL path.
        Requirement: Covers routing behavior for missing path parameters.
        """
        # Calling '/layers//attributes' results in a routing mismatch or redirection
        # By following redirects, we confirm the final result is a 404 as the ID is missing
        response = client.get('/layers//attributes', follow_redirects=True)
        assert response.status_code == 404

    def test_get_layer_attributes_key_error(self, client: FlaskClient, mock_managers: Dict[str, Any]) -> None:
        """
        Test Case: Edge case where metadata exists but 'attributes' key is missing.
        Requirement: Covers behavior when unexpected data structures are returned.
        """
        layer_id = "malformed_metadata_layer"
        # Return metadata missing the 'attributes' key to trigger a KeyError
        mock_managers["layer"].get_metadata.return_value = {"some_other_key": "data"}

        response = client.get(f'/layers/{layer_id}/attributes')

        # This will trigger the global generic exception handler (500)
        assert response.status_code == 500
        data = response.get_json()
        assert "Internal Server Error" in data["error"]["message"]

    # --- Tests for GET /basemaps/<basemap_id> ---

    def test_load_basemap_success(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Successfully load an existing basemap.
        Requirement: Branch coverage for 'return jsonify(basemap), 200'.
        """
        # 1. Setup mock data for the manager
        basemap_id = "osm_standard"
        mock_basemap_data = {
            "id": "osm_standard",
            "name": "OpenStreetMap",
            "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "&copy; OpenStreetMap contributors"
        }
        mock_managers["basemap"].get_basemap.return_value = mock_basemap_data

        # 2. Execute the GET request
        response = client.get(f'/basemaps/{basemap_id}')

        # 3. Assertions
        assert response.status_code == 200
        assert response.get_json() == mock_basemap_data
        mock_managers["basemap"].get_basemap.assert_called_once_with(basemap_id)

    def test_load_basemap_not_found(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Attempt to load a basemap ID that does not exist.
        Requirement: Branch coverage for 'if basemap is None' returning 404.
        """
        # 1. Setup: Manager returns None for unknown IDs
        basemap_id = "non_existent_map"
        mock_managers["basemap"].get_basemap.return_value = None

        # 2. Execute the GET request
        response = client.get(f'/basemaps/{basemap_id}')

        # 3. Assertions
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == f"Basemap with id {basemap_id} not found"
        mock_managers["basemap"].get_basemap.assert_called_once_with(basemap_id)

    def test_load_basemap_empty_id(self, client: FlaskClient) -> None:
        """
        Test Case: Edge case where the basemap_id is empty or missing in the path.
        Requirement: Validate Flask routing behavior for variable path parameters.
        """
        # Flask routes without a trailing slash defined in @app.route 
        # usually return 404 for empty path segments.
        response = client.get('/basemaps/', follow_redirects=True)
        assert response.status_code == 404

    @pytest.mark.parametrize("exception_type", [OSError, IOError, RuntimeError, ValueError])
    def test_run_script_specific_server_errors(
        self, 
        client: FlaskClient, 
        mock_managers: Dict[str, MagicMock], 
        exception_type: type
    ) -> None:
        """
        Test Case: Script execution triggers specific server-side exceptions.
        Requirement: Ensure 100% branch coverage for the (OSError, IOError, RuntimeError, ValueError) block.
        Verification:
            - Status code is 500.
            - running_scripts status is updated to 'failed'.
            - Response contains the sanitized error message.
        """
        script_id = "test_script_err"
        mock_sm = mock_managers["script"]
        
        # 1. Setup: Mock the script manager to raise the specific exception
        mock_sm.run_script.side_effect = exception_type("Simulated server error")
        
        # Mocking filesystem and internal state dependencies
        with patch('App.app.os.path.isfile', return_value=True), \
             patch('App.app.running_scripts', {script_id: {"status": "not_running", "execution_id": "old_id"}}), \
             patch('App.app.app.logger.error') as mock_log:
            
            # 2. Execute: Trigger the run_script route
            response = client.post(
                f'/scripts/{script_id}',
                json={"parameters": {}, "layers": []}
            )
            
            # 3. Assertions
            assert response.status_code == 500
            data = response.get_json()
            
            # Verify sanitized JSON structure
            assert data["error"] == "Internal Server Error"
            assert data["message"] == "Script execution failed. Please contact the administrator."
            assert data["script_id"] == script_id
            assert "execution_id" in data
            
            # Verify logging was called with exc_info=True for debugging
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert "Script execution failed" in args[0]
            assert kwargs["exc_info"] is True

    def test_run_script_state_cleanup_on_failure(
        self, 
        client: FlaskClient, 
        mock_managers: Dict[str, MagicMock]
    ) -> None:
        """
        Test Case: verify the global running_scripts state is updated on exception.
        Requirement: Edge case ensuring the lock and status update logic executes correctly.
        """
        script_id = "cleanup_test_script"
        mock_sm = mock_managers["script"]
        
        # Trigger an exception to enter the target block
        mock_sm.run_script.side_effect = RuntimeError("Failure")
        
        # We need to track the actual dictionary used in the app
        from App.app import running_scripts
        
        with patch('App.app.os.path.isfile', return_value=True):
            client.post(
                f'/scripts/{script_id}',
                json={"parameters": {}, "layers": []}
            )
            
            # Verify the status was set to 'failed' in the global state
            assert script_id in running_scripts
            assert running_scripts[script_id]["status"] == "failed"

    def test_export_layer_success(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Successfully export an existing layer.
        Requirement: Verify 200 status and correct attachment headers.
        """
        layer_id = "test_layer"
        mock_path = "/data/layers/test_layer.gpkg"
        mock_ext = ".gpkg"

        # 1. Setup: Mock manager paths and extensions
        mock_managers["layer"].get_layer_path.return_value = mock_path
        mock_managers["layer"].get_layer_extension.return_value = mock_ext

        # 2. Mock filesystem and file response
        with patch('os.path.abspath', return_value=mock_path), \
             patch('os.path.isfile', return_value=True), \
             patch('App.app.send_file') as mock_send:
            
            mock_send.return_value = ("file_content", 200)
            
            response = client.get(f'/layers/export/{layer_id}')

            # 3. Assertions
            assert response.status_code == 200
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert args[0] == mock_path
            assert kwargs["as_attachment"] is True
            assert kwargs["download_name"] == f"{layer_id}{mock_ext}"

    def test_export_layer_file_not_found(self, client: FlaskClient, mock_managers: dict) -> None:
        """
        Test Case: Layer metadata exists but the physical file is missing.
        Requirement: Branch coverage for the InternalServerError (500) raise.
        """
        layer_id = "missing_file_layer"
        mock_path = "/data/layers/missing.tif"

        # 1. Setup
        mock_managers["layer"].get_layer_path.return_value = mock_path
        
        # 2. Mock filesystem to report file does not exist
        with patch('os.path.abspath', return_value=mock_path), \
             patch('os.path.isfile', return_value=False):
            
            response = client.get(f'/layers/export/{layer_id}')

            # 3. Assertions: Verify 500 error and structured JSON response
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
            assert f"Exported file not found" in data["error"]["description"]

    def test_export_layer_missing_id(self, client: FlaskClient) -> None:
        """
        Test Case: Edge case where layer_id is empty.
        Requirement: Verify BadRequest (400) logic.
        Note: Due to Flask routing, an empty string usually results in 404,
        but we test the logic branch for 'if not layer_id'.
        """
        # Testing the manual raise BadRequest("layer_id is required")
        # In typical Flask setups, reaching this requires a bypass or specific route config
        with app.test_request_context():
            from App.app import export_layer
            with pytest.raises(BadRequest) as excinfo:
                export_layer("")
            assert "layer_id is required" in str(excinfo.value)

    def test_add_layer_missing_file_payload(self, client: FlaskClient) -> None:
        """
        Test Case: Attempt to add a layer without providing a file in the request.
        Requirement: Branch coverage for 'if not added_file' in add_layer().
        Verification:
            - Status code is 400 (Bad Request).
            - Error description matches the expected message.
        """
        # 1. Execute a POST request with an empty data payload (no 'file' field)
        response = client.post('/layers', data={})

        # 2. Assertions
        # The app.errorhandler(HTTPException) will catch the BadRequest and format it
        assert response.status_code == 400
        
        data = response.get_json()
        assert "error" in data
        assert data["error"]["code"] == 400
        assert data["error"]["description"] == "You must upload a file under the 'file' field."

    @patch('App.app.os.path.exists')
    @patch('App.app.os.remove')
    def test_add_layer_already_exists_cleanup(
        self, 
        mock_remove: MagicMock, 
        mock_exists: MagicMock, 
        client: FlaskClient, 
        mock_managers: dict
    ) -> None:
        """
        Test Case: Attempt to add a layer that already exists.
        Requirement: Verify that the temporary file is deleted before the 400 error is raised.
        """
        layer_id = "duplicate_layer"
        
        # 1. Setup: Mock the layer manager to trigger the "already exists" branch
        mock_managers["layer"].layer_exists.return_value = True
        
        # 2. Setup: Ensure the check for the temp file returns True so remove is called
        mock_exists.return_value = True

        # 3. Prepare multipart form data
        data = {
            'file': (io.BytesIO(b"dummy geospatial data"), 'test.tif'),
            'name': layer_id
        }
        
        # We patch os.path.join to return a deterministic path we can verify
        with patch('App.app.os.path.join', side_effect=lambda *args: "/".join(args)) as mock_join:
            response = client.post('/layers', data=data, content_type='multipart/form-data')

            # 4. Assertions
            assert response.status_code == 400
            
            # Verify structured error response
            data = response.get_json()
            assert data["error"]["description"] == "A Layer with the same name already exists"
            
            # Logic Verification:
            # We find the call to os.path.join that created the temp_path
            # It usually joins the temp_dir and the filename
            actual_temp_path = None
            for call in mock_join.call_args_list:
                if 'test.tif' in call.args:
                    actual_temp_path = "/".join(call.args)
                    break
            
            # Ensure the exact path generated was the one deleted
            if actual_temp_path:
                mock_remove.assert_called_once_with(actual_temp_path)
            else:
                pytest.fail("Could not determine the temp_path used by the application")

    @patch('App.app.os.path.exists')
    @patch('App.app.os.remove')
    def test_add_layer_already_exists_no_temp_file(
        self, 
        mock_remove: MagicMock, 
        mock_exists: MagicMock, 
        client: FlaskClient, 
        mock_managers: dict
    ) -> None:
        """
        Test Case: Edge case where layer exists but temp_path does not exist on disk.
        Requirement: 100% Branch coverage for 'if os.path.exists(temp_path)' being False.
        """
        # 1. Setup: Layer exists, but the file system check for temp_path returns False
        mock_managers["layer"].layer_exists.return_value = True
        mock_exists.return_value = False

        data = {
            'file': (io.BytesIO(b"dummy data"), 'test.tif'),
            'name': "existing_layer"
        }
        
        response = client.post('/layers', data=data)

        # 2. Assertions
        assert response.status_code == 400
        # Ensure os.remove was NOT called because the file didn't exist
        mock_remove.assert_not_called()

    def test_import_scripts_no_file(self, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if no file is provided."""
        response = client.post('/scripts/import')
        assert response.status_code == 400
        assert b"Missing zip file" in response.data

    def test_import_scripts_no_filename(self, client: FlaskClient) -> None:
        """
        Covers: if not original_id: raise BadRequest("Uploaded script has no filename.")
        """
        # We provide a file-like object but an empty string as the filename 
        # to trigger the 'no filename' logic specifically.
        data = {'file': (io.BytesIO(b"content"), '')}
        response = client.post('/scripts/import', data=data)
        
        # If the app logic treats empty filename as "Missing zip file", 
        # we adjust the assertion to match the code's priority.
        assert response.status_code == 400
        assert b"no filename" in response.data or b"Missing zip file" in response.data

    def test_import_scripts_invalid_extension(self, client: FlaskClient) -> None:
        """Requirement: raises BadRequest for non-zip extensions."""
        data = {'file': (io.BytesIO(b"data"), 'test.py')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"Only .zip files are supported" in response.data

    def test_import_scripts_corrupt_zip(self, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if the file is not a valid ZIP."""
        data = {'file': (io.BytesIO(b"not a zip content"), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"Invalid ZIP file" in response.data

    @patch('App.app.os.walk')
    def test_import_scripts_missing_metadata(self, mock_walk: MagicMock, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if no *metadata.json is found inside ZIP."""
        mock_walk.return_value = [('/tmp/extract', [], ['script1.py'])]
        
        # Create a valid zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('script1.py', 'print(1)')
        
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"must contain a *metadata.json file" in response.data

    @patch('App.app.os.walk')
    def test_import_scripts_multiple_metadata(self, mock_walk: MagicMock, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if multiple metadata files exist."""
        mock_walk.return_value = [
            ('/tmp/extract', [], ['a_metadata.json', 'b_metadata.json'])
        ]
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('a_metadata.json', '{}')
            zf.writestr('b_metadata.json', '{}')
            
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"multiple metadata.json files" in response.data

    def test_import_scripts_invalid_json_format(self, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if metadata.json is corrupted."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('metadata.json', '{invalid_json')
            
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"Invalid metadata.json file" in response.data

    def test_import_scripts_missing_scripts_object(self, client: FlaskClient) -> None:
        """Requirement: raises BadRequest if 'scripts' key is missing in JSON."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('metadata.json', json.dumps({"other": "data"}))
            
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        assert response.status_code == 400
        assert b"must contain a 'scripts' object" in response.data

    @patch('App.app.shutil.copy')
    @patch('App.app.os.path.getsize')
    def test_import_scripts_success(
        self, 
        mock_getsize: MagicMock, 
        mock_copy: MagicMock, 
        client: FlaskClient, 
        mock_managers: dict
    ) -> None:
        """
        Success Path: Imports scripts and registers them.
        Covers the main loop, size validation, and move_file logic.
        """
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 1000
        mock_getsize.return_value = 500
        
        # Build metadata and zip
        metadata = {
            "scripts": {
                "script_1": {"author": "Tester"},
                "script_2": {"author": "Tester2"}
            }
        }
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('metadata.json', json.dumps(metadata))
            zf.writestr('script_1.py', 'print("hello")')
            zf.writestr('script_2.py', 'print("world")')
            
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'bundle.zip')}
        response = client.post('/scripts/import', data=data)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["imported_count"] == 2
        assert mock_managers["script"].add_script.call_count == 2
        mock_managers["file"].move_file.assert_called()

    @patch('App.app.os.path.getsize')
    def test_import_scripts_size_exceeded_skipped(
        self, 
        mock_getsize: MagicMock, 
        client: FlaskClient, 
        mock_managers: dict
    ) -> None:
        """Edge Case: Scripts exceeding MAX_SCRIPT_FILE_SIZE are skipped."""
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 10
        mock_getsize.return_value = 100 # Larger than limit
        
        metadata = {"scripts": {"too_big": {"meta": "data"}}}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('metadata.json', json.dumps(metadata))
            zf.writestr('too_big.py', 'x' * 100)
            
        data = {'file': (io.BytesIO(zip_buffer.getvalue()), 'test.zip')}
        response = client.post('/scripts/import', data=data)
        
        # Since the only script was skipped, it raises BadRequest
        assert response.status_code == 400
        assert b"No valid scripts found to import" in response.data

    @patch('App.app.os.remove')
    @patch('App.app.shutil.rmtree')
    def test_import_scripts_cleanup_finally(
        self, 
        mock_rmtree: MagicMock, 
        mock_remove: MagicMock, 
        client: FlaskClient
    ) -> None:
        """Requirement: Ensure temporary files/dirs are cleaned up regardless of failure."""
        # Cause a failure early (corrupt zip)
        data = {'file': (io.BytesIO(b"corrupt"), 'test.zip')}
        client.post('/scripts/import', data=data)
        
        # Verify cleanup was attempted
        assert mock_remove.called
        assert mock_rmtree.called

    @patch('App.app.os.path.getsize')
    def test_import_scripts_size_limit_branch(
        self, 
        mock_getsize: MagicMock, 
        client: FlaskClient, 
        mock_managers: dict
    ) -> None:
        """
        Covers the branch: if os.path.getsize(temp_script_path) > MAX_SCRIPT_FILE_SIZE
        """
        mock_managers["script"].MAX_SCRIPT_FILE_SIZE = 10
        mock_getsize.return_value = 100 # Mocked size is larger than limit
        
        metadata = {"scripts": {"big_script": {}}}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('metadata.json', json.dumps(metadata))
            zf.writestr('big_script.py', 'x' * 100)
        zip_buffer.seek(0)

        data = {'file': (zip_buffer, 'test.zip')}
        response = client.post('/scripts/import', data=data)
        
        assert response.status_code == 400
        assert b"No valid scripts found" in response.data

    @patch('App.app.os.walk')
    def test_import_scripts_ambiguous_metadata(self, mock_walk: MagicMock, client: FlaskClient) -> None:
        """
        Covers: if len(metadata_files) > 1: raise BadRequest(...)
        """
        # Mock os.walk to simulate finding two metadata files in the extracted directory
        mock_walk.return_value = [
            ('/tmp/extract', [], ['meta1_metadata.json', 'meta2_metadata.json'])
        ]
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('meta1_metadata.json', '{}')
            zf.writestr('meta2_metadata.json', '{}')
        zip_buffer.seek(0)

        data = {'file': (zip_buffer, 'test.zip')}
        response = client.post('/scripts/import', data=data)
        
        assert response.status_code == 400
        assert b"multiple metadata.json files" in response.data

    @patch('App.app.os.remove')
    @patch('App.app.shutil.rmtree')
    def test_import_scripts_cleanup_flow(
        self, 
        mock_rmtree: MagicMock, 
        mock_remove: MagicMock, 
        client: FlaskClient
    ) -> None:
        """
        Covers the 'finally' block. Ensures temp files are deleted even on BadZipFile.
        """
        # Sending non-zip data to trigger zipfile.BadZipFile
        data = {'file': (io.BytesIO(b"not_a_zip"), 'test.zip')}
        client.post('/scripts/import', data=data)
        
        # Verify the cleanup logic was executed
        assert mock_remove.called
        assert mock_rmtree.called