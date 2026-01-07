
import json
from flask import Flask, request, after_this_request, jsonify, send_file, abort, g
from werkzeug.exceptions import HTTPException, BadRequest, NotFound, InternalServerError, UnprocessableEntity
import geopandas as gpd
import shutil
import os
import ast
import zipfile
from .FileManager import FileManager
from .BasemapManager import BasemapManager
from .LayerManager import LayerManager
from .ScriptManager import ScriptManager
from .DataManager import DataManager
from .LogManager import LogManager
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import uuid
from threading import Lock
import time

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from PIL import Image
import io
import numpy as np

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
    """Handles standard HTTP errors (404, 405, etc.)"""
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
    """Handles unexpected errors gracefully"""
    app.logger.error(
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
    """Handles unexpected errors gracefully"""
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
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())

@app.after_request
def log_response(response):
    duration = round(time.time() - g.start_time, 6)

    app.logger.info(
        "[%s] %s %s %s %ss",
        g.request_id,
        request.method,
        request.path,
        response.status_code,
        duration
    )

    return response


log_manager = LogManager(disable_console=True,)

log_manager.configure_flask_logger(app)

@app.route('/')
def home():
    return "GeoDummy backend is running!!!\n By SoftMinds"

# Script Management Endpoints

'''
Use Case: UC-B-09
'''
@app.route('/scripts', methods=['POST'])
def add_script():
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

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        abort(500, description="Failed to store script.")

    return jsonify({"message": f"Script added successfully", "script_id": script_id, "metadata": metadata}), 200

'''
Use Case: UC-B-10
'''
@app.route('/scripts/<script_id>', methods=['GET'])
def script_metadata(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")

    try:
        metadata = script_manager.get_metadata(script_id)
    except FileNotFoundError:
        # ficheiro script_id_metadata.json não existe
        raise NotFound(f"Metadata not found for script_id={script_id}")
    except ValueError as e:
        # erro a ler/parsear o JSON, por exemplo
        raise BadRequest(str(e))
    except Exception as e:
        # fallback para erros inesperados
        raise InternalServerError(str(e))

    return jsonify({"script_id": script_id, "output": metadata}), 200

'''
Use Case: UC-B-10
'''
@app.route('/scripts', methods=['GET'])
def list_scripts():
    scripts_ids, scripts_metadata = script_manager.list_scripts()

    app.logger.info(
        "[%s] %s",
        g.request_id,
        f"Listed {len(scripts_ids)} scripts and {len(scripts_metadata)} metadata entries"
    )

    return  jsonify({"scripts_ids": scripts_ids, "scripts_metadata": scripts_metadata}), 200

# Script Execution Endpoints

'''
Implements UC-B-11, UC-B-12 and UC-B-13, UC-B-14 is in the background
'''
@app.route('/scripts/<script_id>', methods=['POST'])
def run_script(script_id):
    if not script_id:
        raise BadRequest("script_id is required")
    
    # Begin script execution workflow
    with running_scripts_lock:
        # Check if another script is already running
        if script_id in running_scripts and running_scripts[script_id]["status"] == "running":
            return jsonify({
                    "error": "Conflict",
                    "message": f"Script '{script_id}' is already running. Only one script can be run at a time.",
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
        elif exec_status == "failure":
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
        elif exec_status == "success":
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
            else:
                return jsonify({
                    "message": f"Script '{script_id}' executed successfully with no output",
                    "execution_id": execution_id,
                    "log_path": log_path
                }), 200

        # Unknown status (shouldn't happen, but handle anyway)
        else:
            with running_scripts_lock:
                running_scripts[script_id]["status"] = "failed"
            
            return jsonify({
                "error": "Internal Server Error",
                "message": f"Unknown execution status: {exec_status}",
                "script_id": script_id,
                "execution_id": execution_id,
                "log_path": log_path
            }), 500
        
    
    except BadRequest as e:
        # Client errors (4xx) - re-raise to be handled by Flask
        with running_scripts_lock:
            running_scripts[script_id]["status"] = "failed"
        raise
    
    except Exception as e:
        # Generic server errors - 500 Internal Server Error
        with running_scripts_lock:
            running_scripts[script_id]["status"] = "failed"
        
        # Log the full error server-side for debugging
        app.logger.error(f"Script execution failed: {script_id} (execution_id: {execution_id})", exc_info=True)
        
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
    basemap = basemap_manager.get_basemap(basemap_id)

    if basemap is None:
        return jsonify({"error": f"Basemap with id {basemap_id} not found"}), 404

    return jsonify(basemap), 200 

@app.route('/basemaps', methods=['GET'])
def list_basemaps():
    return jsonify(basemap_manager.list_basemaps()), 200

# Layer Management Endpoints
@app.route('/layers', methods=['GET'])
def list_layers():

    layer_ids = []
    metadata = []

    for filename in os.listdir(file_manager.layers_dir):
        # We only care about metadata files
        if filename.endswith("_metadata.json"):
            layer_id = filename.replace("_metadata.json", "")
            metadata_path = os.path.join(file_manager.layers_dir, filename)

            # Read metadata file
            try:
                with open(metadata_path, "r") as f:
                    layer_metadata = json.load(f)
            except Exception:
                layer_metadata = None
                layer_id = None  
            layer_ids.append(layer_id)
            metadata.append(layer_metadata)

    return jsonify({ "layer_id": layer_ids, "metadata": metadata}), 200


'''
Use Case: UC-B-01
Use Case: UC-B-02
Use Case: UC-B-03
Use Case: UC-B-04
'''
@app.route('/layers', methods=['POST'])
def add_layer():    
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
            raise BadRequest("Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj).")
        
        case ".zip":
            layer_id, metadata = layer_manager.add_shapefile_zip(temp_path,file_name)
        
        case ".geojson":        
            layer_id, metadata = layer_manager.add_geojson(temp_path,file_name)
        
        case ".tif" | ".tiff":
            layer_id, metadata = layer_manager.add_raster(temp_path,file_name)
        
        case ".gpkg":
            layer_id, metadata = layer_manager.add_gpkg_layers(temp_path, selected_layers=selected_layers if selected_layers else None)

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

    file_name, file_extension = os.path.splitext(added_file.filename)

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
        raise BadRequest(str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

'''
UC-B-16
'''
@app.route('/layers/<layer_id>', methods=['GET'])
def get_layer(layer_id):
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

@app.route('/layers', methods=['GET'])
def list_layer_ids_endpoint():
    ids, metadata = layer_manager.list_layer_ids()
    return jsonify({"layer_ids": ids, "metadata": metadata}), 200



'''
UC-B-16
'''
@app.route("/layers/<layer_id>/tiles/<int:z>/<int:x>/<int:y>.png")
def serve_tile(layer_id, z, x, y, tile_size=256):
    
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
                except Exception as e:
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
        raise ValueError(f"Error serving tile: {e}")
    
@app.route('/layers/<layer_id>/preview.png', methods=['GET'])
def get_layer_preview(layer_id):
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
            else:
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
                    raise ValueError(f"Error reading raster window: {e}")        
            
            # Save to cache
            img.save(cache_file, format="PNG")

            layer_manager.clean_raster_cache(file_manager.raster_cache_dir)

            # Return as PNG
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            return send_file(img_bytes, mimetype="image/png")

    except Exception as e:
        raise ValueError(f"Error serving tile: {e}")


@app.route('/layers/<layer_id>', methods=['PUT'])
def export_layer(layer_id):    
    data = request.get_json()

    if not layer_id:
        raise BadRequest("layer_id is required")

    # TODO: remove layer

    return jsonify({"message": f"Layer {layer_id} exported"}), 200

@app.route('/layers/<layer_id>', methods=['DELETE'])
def remove_layer(layer_id):    
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
        raise InternalServerError(f"Failed to remove layer {layer_id}: {str(e)}")
    
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

'''
Use Case: UC-B-020
'''
@app.route('/layers/<layer_id>/information', methods=['GET'])
def identify_layer_information(layer_id):
    try:
        info = layer_manager.get_layer_information(layer_id)
        return jsonify({"layer_id": layer_id, "info": info}), 200
    except ValueError as e:
        raise ValueError(f"Error in identifying layer information: {e}")


'''
Use Case: UC-B-05
'''
@app.route('/layers/<layer_id>/attributes', methods=['GET'])
def get_layer_attributes(layer_id):
    if not layer_id:
        raise BadRequest("layer_id parameter is required")
    try:
        data = layer_manager.get_metadata(layer_id)["attributes"]
        return jsonify({"layer_id": layer_id, "attributes": data}), 200
    except ValueError as e:
        raise NotFound(f"Error in retrieving layer attributes: {e}")



'''
Use Case: UC-B-06
'''
@app.route('/layers/<layer_id>/table', methods=['GET'])
def extract_data_from_layer_for_table_view(layer_id):
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
    import fiona
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

