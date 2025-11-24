
from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import HTTPException, BadRequest
import geopandas as gpd
import shutil
import os
import zipfile
import FileManager
from BasemapManager import BasemapManager

app = Flask(__name__)
file_manager = FileManager.FileManager()
basemap_manager = BasemapManager()

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
        
    
    # If the file is already in GeoJSON or TIFF format, copy it directly to output directory
    if file_extension.lower() in ['.geojson', '.tif']:
        try:
            file_manager.copy_file(temp_path, file_manager.input_dir)
        except ValueError as e:
            os.remove(temp_path)
            return jsonify({"error": str(e)}), 400
    
    # Otherwise, convert it to GeoJSON first, then move to output directory
    else:
        converted_file_path = file_manager.convert_to_geojson(temp_path)

        try:
            file_manager.move_file(converted_file_path, file_manager.input_dir)
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

    # Send file to browser for download
    return send_file(
        source_path,
        as_attachment=True,        # Forces download instead of inline display
        download_name=file_id      # Sets the filename for download
    )


# Script Management Endpoints

@app.route('/scripts', methods=['POST'])
def add_script():

    # TODO: Implement script upload
    
    script_id = "script123"
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

@app.route('/layers', methods=['POST'])
def add_layer():    
    layer_file = request.files['layer_file']
    if not layer_file:
        raise BadRequest("No layer file provided")
    name = request.form.get('layer_name', layer_file.filename)

    # TODO: process and add layer
    layer_id = "layer123"
    return jsonify({"message": f"Layer '{name}' added successfully", "layer_id": layer_id}), 200

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
    if not layer_id:
        raise BadRequest("layer_id parameter is required")

    # TODO: extract information

    return jsonify({"layer_id": layer_id, "info": {"geometry": "Polygon", "features": 124}}), 200

@app.route('/layers/<layer_id>/table', methods=['GET'])
def extract_data_from_layer_for_table_view(layer_id):
    if not layer_id:
        raise BadRequest("layer_id parameter is required")

    # TODO: extract data from file

    table_data = [{"name": "Feature 1", "type": "Polygon"}, {"name": "Feature 2", "type": "Line"}]
    return jsonify({"layer_id": layer_id, "table_data": table_data}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

