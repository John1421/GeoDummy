
import json
from flask import Flask, request, after_this_request, jsonify, send_file
from werkzeug.exceptions import HTTPException, BadRequest, NotFound
import geopandas as gpd
import shutil
import os
import ast
import zipfile
import FileManager
from BasemapManager import BasemapManager
from LayerManager import LayerManager
from ScriptManager import ScriptManager
from DataManager import DataManager
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from functools import lru_cache


ALLOWED_EXTENSIONS = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}
MAX_LAYER_FILE_SIZE_MB = 500

app = Flask(__name__)
CORS(app,origins=["http://localhost:5173"])
file_manager = FileManager.FileManager()
basemap_manager = BasemapManager()
layer_manager = LayerManager()
script_manager = ScriptManager()
data_manager = DataManager()



@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handles standard HTTP errors (404, 405, etc.)"""
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
    app.logger.error(f"Unhandled Exception: {e}")
    return jsonify({
        "error": {
            "code": 500,
            "message": "Internal Server Error",
            "details": str(e)
        }
    }), 500


@app.route('/')
def home():
    return "Flask backend is running 2.0!\n"


# Files Management Endpoints

@app.route('/files', methods=['POST'])
def add_file():
    # Accept file from the browser via multipart/form-data
    added_file = request.files.get('file')
    if not added_file:
        raise BadRequest("You must upload a file under the 'file' field.")
    
    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)


    _, file_extension = os.path.splitext(added_file.filename)

    if file_extension.lower() == ".shp":
        raise BadRequest("Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj).")

    # If its a .zip file, check if it has .shp info
    if file_extension.lower() == '.zip':
        extension_dict = {
            ".shp": 0,
            ".shx": 0,
            ".dbf": 0,
            ".prj": 0,
        }

        # Removes .zip extension from the full path text: 'path/zipfile.zip' --> 'path/zipfile'
        extracted_folder_path = os.path.splitext(temp_path)[0]
        # Then we take this new folder name and create a path: 'path/zipfile' --> path/zipfile/
        os.makedirs(extracted_folder_path, exist_ok = True)

        with zipfile.ZipFile(temp_path, 'r') as zip_contents:
            zip_contents.extractall(extracted_folder_path)

        # Get the file names in the extracted folder directory
        for root, _, files in os.walk(extracted_folder_path):
            for file in files:
                match os.path.splitext(file)[1]:
                    case ".shp":
                        extension_dict[".shp"] += 1
                        # Get the path of the .shp file (if more or less than one it will get caught later on)
                        temp_path = os.path.join(root, file)
                    case ".shx":
                        extension_dict[".shx"] += 1
                    case ".dbf":
                        extension_dict[".dbf"] += 1
                    case ".prj":
                        extension_dict[".prj"] += 1
                    case _:
                        continue

        if extension_dict[".shp"] != 1 or extension_dict[".shx"] != 1 or extension_dict[".dbf"] != 1 or extension_dict[".prj"] > 1:
            raise BadRequest("The provided .zip file has an incorrect amount of files. " +
                             "Please ensure only one file of the types .shp, .shx, .dbf and either one or no .prj files.")
        
        elif extension_dict[".prj"] == 0:
            app.logger.warning("The provided zip file has no .prj file. Proceeding with conversion and addition anyway.")
        
    
    # If the file is already in GeoJSON or TIFF format, copy it directly to layers directory
    if file_extension.lower() in ['.geojson', '.tif']:
        try:
            file_manager.copy_file(temp_path, file_manager.layers_dir)
        except ValueError as e:
            os.remove(temp_path)
            return jsonify({"error": str(e)}), 400
    
    # Otherwise, convert it to GeoJSON first, then move to layers directory
    else:
        converted_file_path = file_manager.convert_to_geojson(temp_path)

        try:
            file_manager.move_file(converted_file_path, file_manager.layers_dir)
        except ValueError as e:
            os.remove(temp_path)
            return jsonify({"error": str(e)}), 400
    
    # Cleanup all the temporary files/folders
    if file_extension.lower() == ".zip":
        shutil.rmtree(extracted_folder_path)
    else:
        os.remove(temp_path)

    return jsonify({"message": f"File added successfully"}), 200

@app.route('/files/<file_id>', methods=['GET'])
def export_file(file_id):

    if not file_id:
        raise BadRequest("file_id was not provided.")
    
    source_path = os.path.join(file_manager.temp_dir, file_id)

    # Check if file exists
    if not os.path.isfile(source_path):
        return jsonify({"error": "File not found"}), 404
    
    # Destination path in layers folder
    output_path = os.path.join(file_manager.layers_dir, file_id)

    # Copy to layers folder (for later selection)
    try:
        file_manager.copy_file(source_path, file_manager.layers_dir)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Send file to browser for download
    return send_file(
        output_path,
        as_attachment=True,        # Forces download instead of inline display
        download_name=file_id      # Sets the filename for download
    )


# Script Management Endpoints

@app.route('/scripts', methods=['POST'])
def add_script():
    # Accept file from the browser via multipart/form-data
    added_file = request.files.get('file')
    if not added_file:
        raise BadRequest("You must upload a file under the 'file' field.")
    
    # Get parameters (sent as regular form fields)
    parameters = request.form.to_dict()

    if not parameters:
        raise BadRequest("You must provide at least one parameter in the request.")

    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)

    script_id, file_extension = os.path.splitext(added_file.filename)

    if file_extension.lower() != ".py":
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest("This programm only accepts python scripts")


    if script_manager.check_script_name_exists(script_id):
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest("A Layer with the same name already exists")
    

    file_manager.move_file(temp_path, file_manager.scripts_dir)
    script_manager.add_script(script_id, parameters)

    return jsonify({"message": f"Script added successfully", "script_id": script_id}), 200

@app.route('/scripts/<script_id>', methods=['DELETE'])
def remove_script(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: Implement script removal

    return jsonify({"message": f"Script {script_id} removed successfully"}), 200

@app.route('/scripts', methods=['GET'])
def list_scripts():

    # TODO: Implement script listing
    scripts = ["script001", "script002", "script003"]
    return jsonify({"message": f"List of scripts received", "scripts":scripts}), 200


'''
Use Case: UC-B-10
'''
@app.route('/scripts/<script_id>', methods=['GET'])
def script_metadata(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")
    

    # TODO: retrieve metadata

    return jsonify({"script_id": script_id, "output": "Metadata here"}), 200


# Script Execution Endpoints

'''
Implements UC-B-12 and UC-B-13, UC-B-14 is in the backgroung
'''
@app.route('/scripts/<script_id>', methods=['POST'])
def run_script(script_id):
    if not script_id:
        raise BadRequest("script_id is required")
    
    # Parse JSON body
    data = request.get_json()
    if not data:
        raise BadRequest("Request body must be JSON")

    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        raise BadRequest("'parameters' must be a JSON object")

    # Construct file path
    script_path = os.path.join(file_manager.scripts_dir, f"{script_id}.py")

    if not os.path.isfile(script_path):
        raise BadRequest(f"Script '{script_id}' does not exist")
    
    # TODO: Obter um execution ID e criar o folder temporário

    # TODO: Copiar o script para o caminho temporário
    
    # script_manager.run_script() = UC-B-13
    # TODO: Passar o execution ID para a função e o caminho temporário do script
    output = script_manager.run_script(script_path, script_id, parameters)

    if isinstance(output, str) and os.path.isfile(output):
        file_name, file_extension = os.path.splitext(output)
        layer_id = os.path.basename(file_name)
        return send_file(output, as_attachment=True, download_name=f"{layer_id}{file_extension}")
            
    elif output != None:        
        return jsonify({"message": f"Run script {script_id}", "output": output}), 200
    else:
        raise ValueError(f"script {script_id} did not return a output") 

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
    
    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)

    if os.path.getsize(temp_path) > MAX_LAYER_FILE_SIZE_MB * 1024 * 1024:
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
            layer_id, metadata = layer_manager.add_gpkg_layers(temp_path)

        case _: 
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise BadRequest("File extension not supported")

    return jsonify({"layer_id": layer_id, "metadata": metadata}), 200    

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
    return send_file(export_file, as_attachment=True, download_name=f"{layer_id}{extension}")

@app.route('/layers/<layer_id>', methods=['PUT'])
def export_layer(layer_id):    
    data = request.get_json()

    if not layer_id:
        raise BadRequest("layer_id is required")

    # TODO: remove layer

    return jsonify({"message": f"Layer {layer_id} exported"}), 200

@app.route('/layers/<layer_id>', methods=['DELETE'])
def remove_layer(layer_id):    
    data = request.get_json()
    if not layer_id:
        raise BadRequest("layer_id is required")

    # TODO: remove layer

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
        data = layer_manager.get_layer_information(layer_id)
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
    
    
    response = data_manager.check_cache(layer_id)
    if response:
        return jsonify(response), 200
    
    
    
    gdf = layer_manager.get_layer_information(layer_id)["attributes"]

    total_rows = len(gdf)
    # Headers metadata
    headers = []
    sample_row = gdf.iloc[0].to_dict() if total_rows > 0 else {}
    for col in gdf.columns:
        headers.append({
            "name": col,
            "type": data_manager.detect_type(sample_row.get(col)),
            "sortable": True  # All non-geometry fields are sortable
        })

    # Data formatting
    rows = []
    warnings = set()    # warnings as a set to avoid duplicates

    for _, row in gdf.iterrows():
        formatted = {}
        for col, value in row.items():
            formatted[col] = data_manager.format_value_for_table_view(value)

            if value is None:
                warnings.add(f"Null value detected in field '{col}'")

        rows.append(formatted)

    # Contruction of final data
    response_data = {
        "headers": headers,
        "rows": rows,
        "total_rows": total_rows,
        "warnings": list(warnings)
    }
    
    # Caching the data
    data_manager.insert_to_cache(layer_id, response_data, 10)

    return jsonify(response_data), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




# '''
# Use case: UC-B-002
# '''
# @app.route('/scripts/<script_id>/inspect', methods=['GET'])
# def script_in_out_inspect(script_id):
#     '''
#     All configurable inputs (folders, shapefiles, rasters, parameters)
#     come from a JSON configuration file generated by the Backend, out of
#     the API request JSON sent by the frontend, and passed into the script
#     at runtime through the environment variable SCRIPT_PARAMS.

#     Each script must begin by loading parameters like:

#         params = {}
#         if "SCRIPT_PARAMS" in os.environ:
#             with open(os.environ["SCRIPT_PARAMS"]) as f:
#                 params = json.load(f)

#     All input files, folders, and dynamic parameters must be accessed using
#     parameter lookups such as:

#         params["input_folder"]
#         params.get("limite_shp")
#         params.get("resolution", 10)
#         params["raster_file"]

#     This makes the script's required inputs statically detectable because the
#     inspector can parse the script using AST and collect every key accessed from
#     the params dict.

#     Outputs produced by scripts must always be written inside the special folder
#     "temp_dir", which is created uniquely for each script execution. Scripts may
#     generate outputs through patterns such as:

#         "temp_dir/output.gpkg"
#         gdf.to_file("temp_dir/curvas.shp")
#         open("temp_dir/report.txt", "w")
#         os.path.join(temp_dir, "summary.json")

#     The inspector scans the script for these output paths (string literals,
#     to_file calls, open() calls, or os.path.join with a temp_dir alias) to build
#     a complete list of output artifacts the script will generate.

#     This unified model allows the backend to:
#     - Know exactly which inputs a script expects (parameter keys)
#     - Know exactly which outputs the script will create (paths under temp_dir)
#     - Validate user input before execution
#     - Generate SCRIPT_PARAMS automatically from user-provided files
#     - Ensure deterministic, safe introspection without executing the script
#     - Provide metadata for script catalogs, validation, and automation flows

#     This architecture enables static script inspection (UC-B-002) while allowing
#     scripts to remain flexible, user-driven, and fully configurable.
#     '''

#     if not script_id:
#         raise BadRequest("script_id parameter is required")
    
#     script_path = f'scripts/{script_id}'
#     if not os.path.exists(script_path):
#         raise BadRequest("script was not found")
    
#     # Results
#     inputs = set()
#     outputs = set()
    
#     # Parse AST
#     with open(script_path, "r") as file:
#         tree = ast.parse(file.read(), filename = script_path)

#     # Track variables assigned to "temp_dir"
#     temp_dir_aliases = set(["temp_dir"])

#     # AST WALK
#     for node in ast.walk(tree):

#         # ========== 1. DETECT INPUT PARAMETERS ==========
#         # params["key"]
#         if isinstance(node, ast.Subscript):
#             if isinstance(node.value, ast.Name) and node.value.id == "params":
#                 # Only support params["key"], not params[variable]
#                 if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
#                     inputs.add(node.slice.value)

#         # params.get("key")
#         if isinstance(node, ast.Call):
#             if isinstance(node.func, ast.Attribute):
#                 if isinstance(node.func.value, ast.Name) and node.func.value.id == 'params':
#                     if node.func.attr == "get" and len(node.args) >= 1:
#                         arg = node.args[0]
#                         if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
#                             inputs.add(arg.value)

#         # ========== 2. DETECT temp_dir ALIASES ==========
#         if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
#             # x = temp_dir
#             if node.value.id in temp_dir_aliases:
#                 for target in node.targets:
#                     if isinstance(target, ast.Name):
#                         temp_dir_aliases.add(target.id)

#         # ========== 3. DETECT OUTPUTS WRITTEN INSIDE temp_dir ==========
#         # A. Strings like "temp_dir/output.shp"
#         if isinstance(node, ast.Constant) and isinstance(node.value, str):
#             path = node.value.replace("\\", "/")
#             if path.startswith("temp_dir"):
#                 outputs.add(path)

#          # B. GeoDataFrame.to_file("temp_dir/...")
#         if isinstance(node, ast.Call) and hasattr(node.func, "attr"):
#             if node.func.attr == "to_file" and node.args:
#                 arg = node.args[0]
#                 if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
#                     path = arg.value.replace("\\", "/")
#                     if path.startswith("temp_dir"):
#                         outputs.add(path)

#         # C. open("temp_dir/...", "w")
#         if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
#             if node.func.id == "open" and node.args:
#                 arg = node.args[0]
#                 if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
#                     path = arg.value.replace("\\", "/")
#                     if path.startswith("temp_dir"):
#                         outputs.add(path)


#         # D. join(temp_dir_alias, "file.ext")
#         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
#             if node.func.attr == "join":
#                 if len(node.args) >= 1:
#                     if isinstance(node.args[0], ast.Name) and node.args[0].id in temp_dir_aliases:
#                         # Extract the file name if literal
#                         if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
#                             filename = node.args[1].value
#                             outputs.add(f"temp_dir/{filename}")

#     # --- Final JSON ---
#     return jsonify({
#         "inputs": sorted(inputs),
#         "outputs": sorted(outputs)
#     }), 200

