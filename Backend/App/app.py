"""
Flask REST API for geospatial data management and script execution.

API Endpoints:
    Script Management:
        POST   /scripts                          - Upload and register a new Python script
        GET    /scripts                          - List all available scripts
        GET    /scripts/<script_id>              - Get metadata for a specific script
        POST   /scripts/<script_id>              - Execute a script with parameters
        DELETE /execute_script/<script_id>       - Stop a running script
        GET    /execute_script/<script_id>       - Get script execution status
        GET    /execute_script/<script_id>/output - Retrieve script output

    Layer Management:
        GET    /layers                           - List all layers with metadata
        POST   /layers                           - Upload and import a new layer
        POST   /layers/preview/geopackage        - Preview GeoPackage layers before import
        GET    /layers/<layer_id>                - Download/export a layer
        DELETE /layers/<layer_id>                - Remove a layer
        POST   /layers/<layer_id>/<priority>     - Set layer display priority
        GET    /layers/export/<layer_id>         - Export layer in original format

    Layer Information:
        GET    /layers/<layer_id>/information    - Get comprehensive layer metadata
        GET    /layers/<layer_id>/attributes     - Get layer attribute field names
        GET    /layers/<layer_id>/table          - Get layer data in tabular format

    Map Rendering:
        GET    /layers/<layer_id>/tiles/<z>/<x>/<y>.png - Serve XYZ map tile
        GET    /layers/<layer_id>/preview.png            - Generate layer preview image

    Basemap Management:
        GET    /basemaps                         - List available basemaps
        GET    /basemaps/<basemap_id>            - Get basemap configuration

Supported Layer Formats:
    Import: .geojson, .gpkg, .zip (shapefiles), .tif/.tiff (rasters)
    Export: .geojson (vectors), .tif (rasters), .zip (multi-layer geopackages)

Configuration:
    - CORS enabled for http://localhost:5173
    - Maximum layer file size: 1000 MB
    - Maximum script file size: 5 MB
    - Script execution timeout: 30 seconds
    - Raster tile size: 256x256 pixels
    - Raster cache management with automatic cleanup

Error Handling:
    All endpoints return standardized JSON error responses with appropriate
    HTTP status codes and are logged with unique request IDs for tracing.

Concurrency:
    Script execution uses a global lock to prevent concurrent execution of scripts.

Logging:
    All requests are logged with unique request IDs, duration, and status codes.
    Execution logs are preserved in the execution directory.
"""

import io
import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from threading import Lock

import fiona
import geopandas as gpd
import numpy as np
import rasterio
from flask import Flask, abort, g, jsonify, request, send_file
from flask_cors import CORS
from PIL import Image
from rasterio.windows import Window
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    InternalServerError,
    NotFound,
)

from .BasemapManager import BasemapManager
from .DataManager import DataManager
from .FileManager import FileManager
from .LayerManager import LayerManager
from .LogManager import LogManager
from .ScriptManager import ScriptManager

ALLOWED_EXTENSIONS = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}


app = Flask(__name__)
CORS(app,origins=["http://localhost:5173"])
file_manager = FileManager()
basemap_manager = BasemapManager()
layer_manager = LayerManager()
script_manager = ScriptManager()
data_manager = DataManager()

running_scripts = {}
running_scripts_lock = Lock()

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """
    Handle and format HTTP exceptions as JSON responses.

    Intercepts Werkzeug HTTPException instances, logs them with the current
    request identifier, and returns a structured JSON error response.

    :param e: The raised HTTP exception.
    :return: Flask response containing a JSON-formatted error.
    """

    app.logger.warning(
        "[%s] %s",
        g.request_id,
        f"HTTP Exception: {e}"
    )
    response = e.get_response()
    response.data = jsonify({
        "error": {
            "code": e.code,
            "name": e.name,
            "description": e.description
        }
    }).data
    response.content_type = "application/json"
    return response

@app.errorhandler(Exception)
def handle_generic_exception(e):
    """
    Handle unexpected uncaught exceptions.

    Logs unhandled exceptions with the current request identifier and returns
    a generic JSON 500 Internal Server Error response.

    :param e: The unhandled exception.
    :return: Flask response with a generic internal server error message.
    """

    app.logger.error(
        """Log an unhandled exception with the current request identifier."""

        "[%s] %s",
        g.request_id,
        f"Unhandled Exception: {e}"
    )
    return jsonify({
        "error": {
            "code": 500,
            "message": "Internal Server Error",
            "details": str(e)
        }
    }), 500

@app.errorhandler(ValueError)
def handle_value_error_exception(e):
    """
    Handle ValueError exceptions raised during request processing.

    Logs the error and returns a JSON-formatted 500 Internal Server Error
    response to the client.

    :param e: The ValueError exception.
    :return: Flask response indicating an internal server error.
    """

    app.logger.error(
        "[%s] %s",
        g.request_id,
        f"Value Error: {e}"
    )
    return jsonify({
        "error": {
            "code": 500,
            "message": "Internal Server Error",
            "details": str(e)
        }
    }), 500


@app.before_request
def before_request():
    """
    Initialize per-request context data.

    Generates a unique request identifier and records the request start time
    for logging and performance measurement purposes.
    """

    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())

@app.after_request
def log_response(response):
    """
    Log request and response metadata after request processing.

    Logs client address, HTTP method, request path, response status code,
    and total request processing duration.

    :param response: The Flask response object.
    :return: The unmodified response.
    """

    duration = round(time.time() - g.start_time, 6)

    app.logger.info(
        "[%s] %s %s %s %s %s",
        g.request_id,
        request.remote_addr,
        request.method,
        request.path,
        response.status_code,
        f"duration: {duration}s"
    )

    return response


log_manager = LogManager(disable_console=False, disable_werkzeug=False)

log_manager.configure_flask_logger(app)


def _sanitize_for_json(data):
    """
    Sanitize data structures to ensure JSON compatibility.

    Recursively replaces NaN and infinite float values with null and
    processes nested dictionaries and lists accordingly.

    :param data: Arbitrary data structure to sanitize.
    :return: JSON-safe version of the input data.
    """

    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    if isinstance(data, dict):
        return {k: _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_json(v) for v in data]
    return data

@app.route('/')
def home():
    """Health-check endpoint indicating the backend is running."""
    return "GeoDummy backend is running!!!\n By SoftMinds"

# Script Management Endpoints

@app.route('/scripts', methods=['POST'])
def add_script():
    """
    Use Case: UC-B-09

    Upload and register a new Python script.

    Validates the uploaded script file and associated metadata, stores the
    script securely, and registers it in the system with a generated identifier.

    :raises BadRequest: If the file, metadata, or validation checks fail.
    :raises InternalServerError: If the script cannot be stored due to a server error.
    :return: JSON response confirming successful script creation.
    """

    # Recieve file from browser via multipart/form-data
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        raise BadRequest("Missing script file under 'file' field.")

    # Recieve metadata
    metadata = request.form.to_dict()
    if not metadata:
        raise BadRequest("Missing script metadata.")

    # Validate filename and extension
    original_id, file_extension = os.path.splitext(uploaded_file.filename)

    if not original_id:
        raise BadRequest("Uploaded script has no filename.")

    if file_extension.lower() != ".py":
        raise BadRequest("Only .py files are supported.")

    # Validate MIME
    if uploaded_file.mimetype not in script_manager.ALLOWED_MIME_TYPES:
        raise BadRequest(f"Unsupported MIME type: {uploaded_file.mimetype}")

    # Generate unique script id
    script_id = str(uuid.uuid4())
    stored_filename = f"{script_id}.py"

    # Store file temporarily in temp_dir
    temp_path = os.path.join(file_manager.temp_dir, stored_filename)
    uploaded_file.save(temp_path)

    try:
        # Validate size
        if os.path.getsize(temp_path) > script_manager.MAX_SCRIPT_FILE_SIZE:
            raise BadRequest("Script file exceeds maximum allowed size.")

        file_manager.move_file(temp_path, file_manager.scripts_dir)
        script_manager.add_script(script_id, metadata)

    except HTTPException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    except (OSError, IOError):
        if os.path.exists(temp_path):
            os.remove(temp_path)
        app.logger.error("Failed to store script", exc_info=True)
        abort(500, description="Failed to store script.")

    return jsonify({
        "message": "Script added successfully",
        "script_id": script_id,
        "metadata": metadata}), 200


@app.route('/scripts/<script_id>', methods=['GET'])
def script_metadata(script_id):
    """
    Use Case: UC-B-10

    Retrieve metadata associated with a stored script.

    Fetches and returns the metadata for the given script identifier,
    typically stored in a corresponding metadata file.

    :param script_id: Unique identifier of the script whose metadata is requested.
    :raises BadRequest: If the script_id is missing or the metadata file is invalid.
    :raises NotFound: If no metadata exists for the given script_id.
    :raises InternalServerError: If an unexpected error occurs while retrieving metadata.
    """

    if not script_id:
        raise BadRequest("script_id parameter is required")

    try:
        metadata = script_manager.get_metadata(script_id)
    except FileNotFoundError as e:
        # ficheiro script_id_metadata.json não existe
        raise NotFound(f"Metadata not found for script_id={script_id}") from e
    except ValueError as e:
        # erro a ler/parsear o JSON, por exemplo
        raise BadRequest(str(e)) from e
    except Exception as e:
        # fallback para erros inesperados
        raise InternalServerError(str(e)) from e

    return jsonify({"script_id": script_id, "output": metadata}), 200


@app.route('/scripts', methods=['GET'])
def list_scripts():
    """
    Use Case: UC-B-10

    List all registered scripts and their metadata.

    Retrieves script identifiers and associated metadata from storage and
    returns them in a JSON response.

    :return: JSON response containing script IDs and metadata.
    """

    scripts_ids, scripts_metadata = script_manager.list_scripts()

    app.logger.info(
        "[%s] %s",
        g.request_id,
        f"Listed {len(scripts_ids)} scripts and {len(scripts_metadata)} metadata entries"
    )

    return  jsonify({"scripts_ids": scripts_ids, "scripts_metadata": scripts_metadata}), 200

# Script Execution Endpoints


@app.route('/scripts/<script_id>', methods=['POST'])
def run_script(script_id):
    """
    Use Case: UC-B-11
    Use Case: UC-B-12
    Use Case: UC-B-13
    Use Case: UC-B-14 is in the background
    
    Execute a stored script with provided parameters.

    Validates input, ensures no conflicting execution is running, executes the
    script, tracks execution status, and returns execution results or errors.

    :param script_id: Identifier of the script to execute.
    :raises BadRequest: If input validation fails or the script does not exist.
    :return: JSON response describing execution outcome.
    """

    if not script_id:
        raise BadRequest("script_id is required")

    # Begin script execution workflow
    with running_scripts_lock:
        # Check if another script is already running
        if script_id in running_scripts and running_scripts[script_id]["status"] == "running":
            return jsonify({
                    "error": "Conflict",
                    "message": f"Script '{script_id}' is already running. " 
                    + "Only one script can be run at a time.",
                    "script_id": script_id,
                    "execution_id": running_scripts[script_id]["execution_id"]
                }), 409


        execution_id = str(uuid.uuid4())
        running_scripts[script_id] = {
            "execution_id": execution_id,
            "start_time": datetime.now(timezone.utc),
            "status": "running"
        }

    try:
        # Parse JSON body
        data = request.get_json()
        if not data:
            raise BadRequest("Request body must be JSON")

        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            raise BadRequest("'parameters' must be a JSON object")

        layers = data.get("layers", {})
        if not isinstance(layers, list):
            raise BadRequest("'layers' must be a JSON list")

        # Construct file path
        script_path = os.path.join(file_manager.scripts_dir, f"{script_id}.py")

        if not os.path.isfile(script_path):
            raise BadRequest(f"Script '{script_id}' does not exist")

        # Execute the script
        output = script_manager.run_script(
            script_path=script_path,
            script_id=script_id,
            execution_id=execution_id,
            data=data,
        )



        exec_status = output.get("status")
        layer_ids = output.get("layer_ids", [])
        metadatas = output.get("metadatas", [])
        log_path = output.get("log_path")

        # Handle timeout (504 Gateway Timeout)
        if exec_status == "timeout":
            with running_scripts_lock:
                running_scripts[script_id]["status"] = "failed"

            return jsonify({
                "error": "Gateway Timeout",
                "message": "Script execution exceeded the maximum allowed time of 30 seconds",
                "script_id": script_id,
                "execution_id": execution_id,
                "timeout_seconds": 30,
                "log_path": log_path
            }), 504

        # Handle failure (500 Internal Server Error)
        if exec_status == "failure":
            with running_scripts_lock:
                running_scripts[script_id]["status"] = "failed"

            return jsonify({
                "error": "Internal Server Error",
                "message": "Script execution failed with errors",
                "script_id": script_id,
                "execution_id": execution_id,
                "log_path": log_path,
                "details": "Check log file for error details"
            }), 500

        # Handle success
        if exec_status == "success":
            # Mark as finished
            with running_scripts_lock:
                running_scripts[script_id]["status"] = "finished"


            # Check if output is a file
            # if outputs and isinstance(outputs[0], str) and os.path.isfile(outputs[0]):
            #     file_path = outputs[0]
            #     file_name, file_extension = os.path.splitext(file_path)
            #     layer_id = os.path.basename(file_name)

            #     file_path_abs = os.path.abspath(file_path)
            #     if not os.path.isfile(file_path_abs):
            #         raise InternalServerError(f"Exported file not found: {file_path_abs}")

            #     return send_file(file_path_abs, as_attachment=True, download_name=f"{layer_id}{file_extension}")

            # Return JSON response
            if layer_ids is not None:
                return jsonify({
                    "message": f"Script '{script_id}' executed successfully",
                    "execution_id": execution_id,
                    "layer_ids": layer_ids,
                    "metadatas": metadatas,
                    "log_path": log_path
                }), 200

            # No output produced
            return jsonify({
                "message": f"Script '{script_id}' executed successfully with no output",
                "execution_id": execution_id,
                "log_path": log_path
            }), 200

        # Unknown status (shouldn't happen, but handle anyway)
        with running_scripts_lock:
            running_scripts[script_id]["status"] = "failed"

        return jsonify({
            "error": "Internal Server Error",
            "message": f"Unknown execution status: {exec_status}",
            "script_id": script_id,
            "execution_id": execution_id,
            "log_path": log_path
        }), 500


    except BadRequest:
        # Client errors (4xx) - re-raise to be handled by Flask
        with running_scripts_lock:
            running_scripts[script_id]["status"] = "failed"
        raise

    except (OSError, IOError, RuntimeError, ValueError):
        # Generic server errors - 500 Internal Server Error
        with running_scripts_lock:
            running_scripts[script_id]["status"] = "failed"

        # Log the full error server-side for debugging
        app.logger.error(
            "Script execution failed: %s (execution_id: %s)",
            script_id,
            execution_id,
            exc_info=True
        )
        # Return sanitized error to client
        return jsonify({
            "error": "Internal Server Error",
            "message": "Script execution failed. Please contact the administrator.",
            "script_id": script_id,
            "execution_id": execution_id
        }), 500

@app.route('/execute_script/<script_id>', methods=['DELETE'])
def stop_script(script_id):
    data = request.get_json()
    if not script_id:
        raise BadRequest("script_id is required")

    # TODO: stop running process

    return jsonify({"message": f"Script {script_id} stopped"}), 200

@app.route('/execute_script/<script_id>', methods=['GET'])
def get_script_status(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")

    '''
    Implementação proposta por Esteves:

def get_script_status(script_id):
    with running_scripts_lock:
        info = running_scripts.get(script_id)

    if not info:
        return jsonify({
            "script_id": script_id,
            "status": "not running"
        }), 200

    return jsonify({
        "script_id": script_id,
        "execution_id": info["execution_id"],
        "status": info["status"],
        "start_time": info["start_time"].isoformat()
    }), 200

    '''

    # TODO: check execution status

    return jsonify({"script_id": script_id, "status": "running"}), 200

@app.route('/execute_script/<script_id>/output', methods=['GET'])
def get_script_output(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: retrieve output

    return jsonify({"script_id": script_id, "output": "Sample output here"}), 200


# Map Interaction Endpoints

@app.route('/basemaps/<basemap_id>', methods=['GET'])
def load_basemap(basemap_id):
    """
    Retrieve a basemap by its identifier.

    Fetches and returns the basemap configuration associated with the given
    basemap identifier.

    :param basemap_id: Identifier of the basemap to retrieve.
    :raises NotFound: If the basemap does not exist.
    :return: JSON response containing the basemap definition.
    """

    basemap = basemap_manager.get_basemap(basemap_id)

    if basemap is None:
        return jsonify({"error": f"Basemap with id {basemap_id} not found"}), 404

    return jsonify(basemap), 200

@app.route('/basemaps', methods=['GET'])
def list_basemaps():
    """
    List all available basemaps.

    Retrieves and returns all basemap configurations registered in the system.

    :return: JSON response containing the list of basemaps.
    """

    return jsonify(basemap_manager.list_basemaps()), 200

# Layer Management Endpoints
@app.route('/layers', methods=['GET'])
def list_layers():
    """
    List all available layers and their metadata.

    Scans the layers directory for metadata files, sanitizes their contents,
    and returns the corresponding layer identifiers and metadata.

    :return: JSON response containing layer IDs and metadata.
    """


    layer_ids = []
    metadata = []

    for filename in os.listdir(file_manager.layers_dir):
        # We only care about metadata files
        if filename.endswith("_metadata.json"):
            layer_id = filename.replace("_metadata.json", "")
            metadata_path = os.path.join(file_manager.layers_dir, filename)

            # Read metadata file
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    layer_metadata = _sanitize_for_json(json.load(f))
                # Only append if successful
                layer_ids.append(layer_id)
                metadata.append(layer_metadata)
            except (OSError, IOError, json.JSONDecodeError):
                # Skip this layer entirely if metadata cannot be read
                continue

    return jsonify({ "layer_id": layer_ids, "metadata": metadata}), 200


@app.route('/layers', methods=['POST'])
def add_layer():
    """
    Use Case: UC-B-01
    Use Case: UC-B-02
    Use Case: UC-B-03
    Use Case: UC-B-04

    Upload and register a new spatial layer.

    Accepts vector or raster data via multipart upload, validates file size and
    format, processes the layer according to its type, and stores its metadata.

    :raises BadRequest: If validation fails or the file format is unsupported.
    :return: JSON response containing created layer IDs and metadata.
    """

    # Accept file from the browser via multipart/form-data
    added_file = request.files.get('file')
    if not added_file:
        raise BadRequest("You must upload a file under the 'file' field.")

    # Get optional selected layers parameter (for geopackages)
    selected_layers = request.form.getlist('layers')

    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)

    if os.path.getsize(temp_path) > layer_manager.MAX_LAYER_FILE_SIZE:
        os.remove(temp_path)
        raise BadRequest("The uploaded file exceeds the maximum allowed size.")

    file_name, file_extension = os.path.splitext(added_file.filename)

    if layer_manager.check_layer_name_exists(file_name):
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest("A Layer with the same name already exists")


    match file_extension.lower():
        case ".shp":
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise BadRequest(
                "Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj)."
                )

        case ".zip":
            layer_id, metadata = layer_manager.add_shapefile_zip(temp_path,file_name)

        case ".geojson":
            layer_id, metadata = layer_manager.add_geojson(temp_path,file_name)

        case ".tif" | ".tiff":
            layer_id, metadata = layer_manager.add_raster(temp_path,file_name)

        case ".gpkg":
            selected_layers = selected_layers if selected_layers else None
            layer_id, metadata = layer_manager.add_gpkg_layers(temp_path, selected_layers=selected_layers)

        case _:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise BadRequest("File extension not supported")


    if not isinstance(layer_id, list):
        layer_id = [layer_id]

    if not isinstance(metadata, list):
        metadata = [metadata]

    return jsonify({"layer_id": layer_id, "metadata": metadata}), 200

@app.route('/layers/preview/geopackage', methods=['POST'])
def preview_geopackage_layers():
    """
    Preview layers inside a GeoPackage file without importing them.
    Useful for allowing users to select which layers to import.
    
    Returns:
        JSON: {"layers": [list of layer names]}
    """
    added_file = request.files.get('file')
    if not added_file:
        raise BadRequest("You must upload a file under the 'file' field.")

    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)

    if os.path.getsize(temp_path) > layer_manager.MAX_LAYER_FILE_SIZE:
        os.remove(temp_path)
        raise BadRequest("The uploaded file exceeds the maximum allowed size.")

    _, file_extension = os.path.splitext(added_file.filename)

    if file_extension.lower() != ".gpkg":
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest("This endpoint only accepts GeoPackage (.gpkg) files.")

    try:
        layers = layer_manager.get_geopackage_layers(temp_path)
        return jsonify({"layers": layers}), 200
    except ValueError as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest(str(e)) from e
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/layers/<layer_id>', methods=['GET'])
def get_layer(layer_id):
    """
    Use Case: UC-B-16

    Export and download a layer.

    Exports the requested layer to an appropriate format and returns it as a
    downloadable file.

    :param layer_id: Identifier of the layer to export.
    :raises BadRequest: If the layer identifier is missing.
    :raises InternalServerError: If the exported file cannot be found.
    :return: File download response.
    """

    if not layer_id:
        raise BadRequest("layer_id is required")

    extension = layer_manager.get_layer_extension(layer_id)

    if extension == ".gpkg":
        export_file = layer_manager.export_geopackage_layer_to_geojson(layer_id)
        extension = ".geojson"
    else:
        export_file = layer_manager.export_raster_layer(layer_id)

    export_file_abs = os.path.abspath(export_file)
    if not os.path.isfile(export_file_abs):
        raise InternalServerError(f"Exported file not found: {export_file_abs}")

    return send_file(export_file_abs, as_attachment=True, download_name=f"{layer_id}{extension}")

'''
@app.route('/layers', methods=['GET'])
def list_layer_ids_endpoint():
    ids, metadata = layer_manager.list_layer_ids()
    return jsonify({"layer_ids": ids, "metadata": metadata}), 200
'''


@app.route("/layers/<layer_id>/tiles/<int:z>/<int:x>/<int:y>.png")
def serve_tile(layer_id, z, x, y, tile_size=256):
    """
    Use Case: UC-B-16

    Serve a map tile for a raster layer.

    Generates or retrieves a cached raster tile for the given layer and tile
    coordinates, returning it as a PNG image.

    :param layer_id: Identifier of the raster layer.
    :param z: Zoom level.
    :param x: Tile X coordinate.
    :param y: Tile Y coordinate.
    :return: PNG image response containing the requested tile.
    """

    # Compute a unique cache filenam
    tile_key = f"{layer_id}_{z}_{x}_{y}.png"
    cache_file = os.path.join(file_manager.raster_cache_dir, tile_key)

    # Serve from cache if it exists
    if os.path.exists(cache_file):
        cache_file_abs = os.path.abspath(cache_file)
        if not os.path.isfile(cache_file_abs):
            raise InternalServerError(f"Cached tile file not found: {cache_file_abs}")
        return send_file(cache_file_abs, mimetype="image/png")

    raster_path = layer_manager.export_raster_layer(layer_id)  # Update with your raster path

    try:
        with rasterio.open(raster_path) as src:

            # Get the tile bounds
            min_lon, min_lat, max_lon, max_lat = layer_manager.tile_bounds(x, y, z)

            # Compute window in raster coordinates
            row_start, col_start = src.index(min_lon, max_lat)  # top-left pixel
            row_stop, col_stop = src.index(max_lon, min_lat)    # bottom-right pixel

            width = col_stop - col_start
            height = row_stop - row_start

            if width <= 0 or height <= 0:
                # Tile outside raster
                img = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
            else:
                # Read window and resample to 256x256
                try:
                    window = Window(col_start, row_start, width, height)
                    data = src.read(
                        window=window,
                        out_shape=(src.count, tile_size, tile_size),
                        resampling=rasterio.enums.Resampling.bilinear
                    )

                    # Convert to image
                    if src.count == 1:
                        img = Image.fromarray(data[0], mode="L")  # single band
                    elif src.count >= 3:
                        img = Image.fromarray(np.dstack(data[:3]), mode="RGB")
                    else:
                        img = Image.fromarray(data[0], mode="L")
                except (rasterio.errors.RasterioError, ValueError, OSError):
                    # In case of any error reading the window, return transparent tile
                    img = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))

            # Save to cache
            img.save(cache_file, format="PNG")

            layer_manager.clean_raster_cache(file_manager.raster_cache_dir)

            # Return as PNG
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            return send_file(img_bytes, mimetype="image/png")

    except Exception as e:
        raise ValueError(f"Error serving tile: {e}") from e

@app.route('/layers/<layer_id>/preview.png', methods=['GET'])
def get_layer_preview(layer_id):
    """
    Generate and retrieve a raster preview image for a layer.

    Creates a PNG preview of the specified raster layer constrained to the
    geographic bounds provided as query parameters. The generated preview
    is cached for subsequent requests.

    :param layer_id: Identifier of the raster layer.
    :raises BadRequest: If the layer identifier or required query parameters are missing.
    :raises InternalServerError: If a cached preview file cannot be found.
    :raises ValueError: If the requested bounds are invalid or the preview cannot be generated.
    :return: PNG image response containing the layer preview.
    """

    if not layer_id:
        raise BadRequest("layer_id is required")

    # Get bounds from query parameters instead of JSON body
    min_lat = request.args.get('min_lat', type=float)
    min_lon = request.args.get('min_lon', type=float)
    max_lat = request.args.get('max_lat', type=float)
    max_lon = request.args.get('max_lon', type=float)

    if None in [min_lat, min_lon, max_lat, max_lon]:
        raise BadRequest("min_lat, min_lon, max_lat, max_lon are required as query parameters")

    # Rest of your code stays the same...
    tile_key = f"{layer_id}_preview.png"
    cache_file = os.path.join(file_manager.raster_cache_dir, tile_key)

    # Serve from cache if it exists
    if os.path.exists(cache_file):
        cache_file_abs = os.path.abspath(cache_file)
        if not os.path.isfile(cache_file_abs):
            raise InternalServerError(f"Cached preview file not found: {cache_file_abs}")
        return send_file(cache_file_abs, mimetype="image/png")

    raster_path = layer_manager.export_raster_layer(layer_id)  # Update with your raster path

    try:
        with rasterio.open(raster_path) as src:

            # Compute window in raster coordinates
            row_start, col_start = src.index(min_lon, max_lat)  # top-left pixel
            row_stop, col_stop = src.index(max_lon, min_lat)    # bottom-right pixel

            width = col_stop - col_start
            height = row_stop - row_start

            if width <= 0 or height <= 0:
                # Tile outside raster
                raise ValueError("Requested bounds are outside the raster extent")

            # Read window and resample to 256x256
            try:
                window = Window(col_start, row_start, width, height)
                data = src.read(window=window)

                # Convert to image
                if src.count == 1:
                    img = Image.fromarray(data[0], mode="L")  # single band
                elif src.count >= 3:
                    img = Image.fromarray(np.dstack(data[:3]), mode="RGB")
                else:
                    img = Image.fromarray(data[0], mode="L")
            except Exception as e:
                # In case of any error reading the window, return transparent tile
                raise ValueError(f"Error reading raster window: {e}") from e

            # Save to cache
            img.save(cache_file, format="PNG")

            layer_manager.clean_raster_cache(file_manager.raster_cache_dir)

            # Return as PNG
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            return send_file(img_bytes, mimetype="image/png")

    except Exception as e:
        raise ValueError(f"Error serving tile: {e}") from e


@app.route('/layers/export/<layer_id>', methods=['GET'])
def export_layer(layer_id):
    """
    Export a layer in its original format.

    Retrieves the stored layer file and returns it as a downloadable attachment.

    :param layer_id: Identifier of the layer to export.
    :raises BadRequest: If the layer identifier is missing.
    :raises InternalServerError: If the layer file cannot be found.
    :return: File download response.
    """

    if not layer_id:
        raise BadRequest("layer_id is required")

    layer = layer_manager.get_layer_path(layer_id)
    extension = layer_manager.get_layer_extension(layer_id)

    export_file_abs = os.path.abspath(layer)
    if not os.path.isfile(export_file_abs):
        raise InternalServerError(f"Exported file not found: {export_file_abs}")

    app.logger.info(
        "[%s] %s",
        g.request_id,
        f"Exported layer {layer}"
    )

    return send_file(export_file_abs, as_attachment=True, download_name=f"{layer_id}{extension}")

@app.route('/layers/<layer_id>', methods=['DELETE'])
def remove_layer(layer_id):
    """
    Remove a layer and its metadata.

    Deletes the layer file and associated metadata from storage.

    :param layer_id: Identifier of the layer to remove.
    :raises BadRequest: If the layer identifier is missing.
    :raises NotFound: If the layer does not exist.
    :raises InternalServerError: If the layer cannot be removed.
    :return: JSON response confirming layer removal.
    """

    if not layer_id:
        raise BadRequest("layer_id is required")

    metadata_path = os.path.join(file_manager.layers_dir, f"{layer_id}_metadata.json")

    layer_path = None
    for ext in [".gpkg", ".tif", ".tiff", ".GPKG", ".TIF", ".TIFF"]:
        candidate = os.path.join(file_manager.layers_dir, f"{layer_id}{ext}")
        if os.path.isfile(candidate):
            layer_path = candidate
            break

    if not layer_path and not os.path.isfile(metadata_path):
        raise NotFound(f"Layer {layer_id} does not exist")

    try:
        if layer_path:
            os.remove(layer_path)

        if os.path.isfile(metadata_path):
            os.remove(metadata_path)

    except OSError as e:
        raise InternalServerError(f"Failed to remove layer {layer_id}: {str(e)}") from e

    return jsonify({"message": f"Layer {layer_id} removed"}), 200

@app.route('/layers/<layer_id>/<priority>', methods=['POST'])
def set_layer_priority(layer_id,priority):
    data = request.get_json()
    if not layer_id:
        raise BadRequest("layer_id is required")
    if not priority:
        raise BadRequest("No priority provided")

    # TODO: set new layer priorities

    return jsonify({"message": "Layer priority updated", "New priority": priority}), 200


# Layer Information Endpoints

@app.route('/layers/<layer_id>/information', methods=['GET'])
def identify_layer_information(layer_id):
    """
    Use Case: UC-B-020

    Retrieve descriptive information about a layer.

    Fetches and returns detailed information describing the given layer.

    :param layer_id: Identifier of the layer.
    :raises ValueError: If the layer information cannot be retrieved.
    :return: JSON response containing layer information.
    """

    try:
        info = layer_manager.get_layer_information(layer_id)
        return jsonify({"layer_id": layer_id, "info": info}), 200
    except ValueError as e:
        raise ValueError(f"Error in identifying layer information: {e}") from e

@app.route('/layers/<layer_id>/attributes', methods=['GET'])
def get_layer_attributes(layer_id):
    """
    Use Case: UC-B-05

    Retrieve attribute metadata for a vector layer.

    Returns the attribute definitions associated with the specified layer.

    :param layer_id: Identifier of the layer.
    :raises BadRequest: If the layer identifier is missing.
    :raises NotFound: If the layer or its attributes cannot be found.
    :return: JSON response containing layer attributes.
    """

    if not layer_id:
        raise BadRequest("layer_id parameter is required")
    try:
        data = layer_manager.get_metadata(layer_id)["attributes"]
        return jsonify({"layer_id": layer_id, "attributes": data}), 200
    except ValueError as e:
        raise NotFound(f"Error in retrieving layer attributes: {e}") from e

@app.route('/layers/<layer_id>/table', methods=['GET'])
def extract_data_from_layer_for_table_view(layer_id):
    """
    Use Case: UC-B-06

    Extract tabular data from a vector layer.

    Reads attribute data from a vector layer, formats it for tabular display,
    and returns headers, rows, and warnings. Results may be cached for efficiency.

    :param layer_id: Identifier of the layer.
    :raises BadRequest: If the layer identifier is missing or refers to a raster.
    :return: JSON response containing table headers, rows, and metadata.
    """

    if not layer_id:
        raise BadRequest("layer_id parameter is required")

    if layer_manager.is_raster(layer_id):
        raise BadRequest("Raster doesn't have attributes")


    response = data_manager.check_cache(layer_id)
    if response:
        return jsonify(response), 200

    # 1) Descobrir caminho do GPKG
    gpkg_path = os.path.join(file_manager.layers_dir, f"{layer_id}.gpkg")
    if not os.path.isfile(gpkg_path):
        raise BadRequest("Vector layer file not found")

    # 2) Ler a primeira layer do GPKG
    layers = fiona.listlayers(gpkg_path)
    if not layers:
        raise BadRequest("No layers found in GeoPackage")
    layer_name = layers[0]

    gdf = gpd.read_file(gpkg_path, layer=layer_name)

    # 3) Remover geometria para tabela
    if "geometry" in gdf.columns:
        gdf = gdf.drop(columns=["geometry"])

    total_rows = len(gdf)

    headers = []
    sample_row = gdf.iloc[0].to_dict() if total_rows > 0 else {}
    for col in gdf.columns:
        headers.append({
            "name": col,
            "type": data_manager.detect_type(sample_row.get(col)),
            "sortable": True
        })

    rows = []
    warnings = set()

    for _, row in gdf.iterrows():
        formatted = {}
        for col, value in row.items():
            formatted[col] = data_manager.format_value_for_table_view(value)
            if value is None:
                warnings.add(f"Null value detected in field '{col}'")
        rows.append(formatted)

    response_data = {
        "headers": headers,
        "rows": rows,
        "total_rows": total_rows,
        "warnings": list(warnings)
    }

    data_manager.insert_to_cache(layer_id, response_data, 10)

    return jsonify(response_data), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
