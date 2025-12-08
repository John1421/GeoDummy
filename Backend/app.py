
from flask import Flask, request, after_this_request, jsonify, send_file
from werkzeug.exceptions import HTTPException, BadRequest
import geopandas as gpd
import shutil
import os
import ast
import zipfile
import FileManager
from BasemapManager import BasemapManager
from LayerManager import LayerManager
from ScriptManager import ScriptManager
from flask_cors import CORS

app = Flask(__name__)
CORS(app,origins=["http://localhost:5173"])
file_manager = FileManager.FileManager()
basemap_manager = BasemapManager()
layer_manager = LayerManager()
script_manager = ScriptManager()

ALLOWED_EXTENSIONS = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}

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

@app.route('/scripts/<script_id>', methods=['GET'])
def script_metadata(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: retrieve metadata

    return jsonify({"script_id": script_id, "output": "Metadata here"}), 200

@app.route('/scripts/<script_id>/inspect', methods=['GET'])
def script_in_out_inspect(script_id):
    if not script_id:
        raise BadRequest("script_id parameter is required")
    
    script_path = f'scripts/{script_id}'

    if not os.path.exists(script_path):
        raise BadRequest("script was not found")
    
    inputs = []
    outputs = []
    
    with open(script_path, "r") as file:
        tree = ast.parse(file.read(), filename = script_path)

    for node in ast.walk(tree):

        # Detect variables assigned to folder paths (strings)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                path = node.value.value.lower()

                # Checks all targets for the assignment 
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        #simple heuristics to detect files of allowed extensions or folders
                        if os.path.isdir(path):
                            inputs.append({"type": "folder", "name": name, "path": path})
                        elif any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                            outputs.append({"type": "file", "name": name, "path": path})


        # Detect calls to GeoDataFrame.to_file (writing output shapefiles)
        if isinstance(node, ast.Call) and hasattr(node.func, "attr"):
            if node.func.attr == "to_file":
                if node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant):
                        path = arg.value.lower()
                        if any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                            outputs.append({"type": "file", "name": "to_file", "path": path})


    return jsonify({"inputs": inputs, "outputs": outputs})


# Script Execution Endpoints

@app.route('/execute_script/<script_id>', methods=['POST'])
def run_script(script_id):
    data = request.get_json()
    if not script_id:
        raise BadRequest("script_id is required")
    parameters = data.get('parameters', {})

    # TODO: Implement script execution logic here

    return jsonify({"message": f"Running script {script_id}", "parameters": parameters}), 200

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

#Requirement FR_028
@app.route('/layers', methods=['POST'])
def add_layer():    
    # Accept file from the browser via multipart/form-data
    added_file = request.files.get('file')
    if not added_file:
        raise BadRequest("You must upload a file under the 'file' field.")
    
    # File is temporarily stored in tmp_dir folder for handling
    temp_path = os.path.join(file_manager.temp_dir, added_file.filename)
    added_file.save(temp_path)

    layer_id, file_extension = os.path.splitext(added_file.filename)

    if layer_manager.check_layer_name_exists(layer_id):
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise BadRequest("A Layer with the same name already exists")


    match file_extension.lower():
        case ".shp":
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise BadRequest("Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj).")
        
        case ".zip":
            layer_manager.add_shapefile_zip(temp_path,layer_id)
            export_file = layer_manager.export_geopackage_layer_to_geojson(layer_id)
            return send_file(export_file, as_attachment=True, download_name=f"{layer_id}.geojson")
        
        case ".geojson":        
            layer_manager.add_geojson(temp_path,layer_id)
            os.remove(temp_path)
            export_file = layer_manager.export_geopackage_layer_to_geojson(layer_id)
            return send_file(export_file, as_attachment=True, download_name=f"{layer_id}.geojson")
        
        case ".tif" | ".tiff":
            layer_manager.add_raster(temp_path,layer_id)
            export_file = layer_manager.export_raster_layer(layer_id)
            return send_file(export_file, as_attachment=True, download_name=f"{layer_id}.tiff")
        
        case ".gpkg":
            new_layers = layer_manager.add_gpkg_layers(temp_path)
            os.remove(temp_path)
            zip_path = os.path.join(file_manager.temp_dir, f"{layer_id}_export.zip")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for layer in new_layers:
                    # Export each layer from the default gpkg
                    exported_geojson = layer_manager.export_geopackage_layer_to_geojson(layer)
                    # Add it into zip
                    zipf.write(exported_geojson, arcname=f"{layer}.geojson")
                    # Optional cleanup
                    os.remove(exported_geojson)

            return send_file(zip_path, as_attachment=True, download_name=f"{layer_id}_layers.zip")
            
        case _: 
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise BadRequest("Fle extension not supported")

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

@app.route('/layers/<layer_id>/information', methods=['GET'])
def identify_layer_information(layer_id):
    try:
        info = layer_manager.get_layer_information(layer_id)
        return jsonify({"layer_id": layer_id, "info": info}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@app.route('/layers/<layer_id>/table', methods=['GET'])
def extract_data_from_layer_for_table_view(layer_id):
    if not layer_id:
        raise BadRequest("layer_id parameter is required")

    _, file_name_ext = os.path.splitext(layer_id)

    # Check if the file extension in supported
    if file_name_ext.lower() != '.gpkg':
        raise BadRequest("layer format not supported")
    
    layer_path = os.path.join(file_manager.layers_dir, layer_id)
    total_data = {}
    
    # Extracts all internal layers from the .gpkg file
    internal_layers = gpd.list_layers(layer_path)

    # Iterating though all the internal layers by name
    for internal_layer in internal_layers["name"]:
        # Read all the data from the layer
        geo_data_frame = gpd.read_file(layer_path, layer=internal_layer)

        # Drop the geometric data, keeping only attributes
        table_data = geo_data_frame.drop(columns = "geometry")

        # Add the new internal_layer entry with its name as a key and the table data as the values
        total_data[internal_layer] = table_data.to_dict(orient = "records")

    return jsonify(total_data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

