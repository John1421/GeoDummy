
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException, BadRequest
import geopandas as gpd
import shutil
import os
app = Flask(__name__)

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

    # Parse JSON body
    data = request.get_json()
    if not data or 'path' not in data:
        raise BadRequest("Missing 'path' in request body")

    path = data['path']

    # Validate the file path
    if not isinstance(path, str) or not os.path.isfile(path):
        raise BadRequest("Invalid file path")
    
    # Extract file name and extension
    file_name_full = os.path.basename(path)

    # Split file name and extension
    file_name, filen_name_ext = os.path.splitext(file_name_full)
    allowed_extensions = { '.geojson', '.shp', '.gpkg', '.tif'}

    # Check if the file extension is supported
    if filen_name_ext.lower() not in allowed_extensions:
        raise BadRequest("Unsupported file type")

    # Get/ensure the existence of input_layers/
    destination_path = './input_layers/'
    if not os.path.exists(destination_path):
        os.makedirs(destination_path) 

    # Process the file based on its type
    if filen_name_ext.lower() == '.geojson' or filen_name_ext.lower() == '.tif':
        try:
            # Simply copy the file to the destination as is
            shutil.copy(path, os.path.join(destination_path, file_name_full))
        except Exception as e:
            raise BadRequest(f"Error copying file: {e}")

    else:
        # Read the file using geopandas
        input_file = gpd.read_file(path)

        try: 
            # Convert and save the file in GeoJSON format
            output_file = os.path.join(destination_path, file_name + '.geojson')
            input_file.to_file(output_file, driver='GeoJSON')
        except Exception as e:
            raise BadRequest(f"Error converting and storing file: {e}")

    return jsonify({"message": f"File added successfully"}), 200

    

@app.route('/files', methods=['PUT'])
def export_file():

    # Parse JSON body
    data = request.get_json()
    if not data or 'destination_path' not in data or 'file_id' not in data:
        raise BadRequest("Missing 'destination_path' or 'file_id' in request body")
    
    destination_path = data['destination_path']
    file_id = data['file_id']

    # Validate destination path
    if not isinstance(destination_path, str) or not os.path.isdir(destination_path):
        raise BadRequest("Invalid destination path")
    
    # Check if there is a file with the same name in the destination path
    if os.path.exists(os.path.join(destination_path, file_id)):
        raise BadRequest("A file with the same name already exists in the destination")

    outputs_folder = './output/'

    # Confirm the existance of output/
    if not os.path.exists(outputs_folder):
        os.makedirs(outputs_folder)

    output_file = os.path.join(outputs_folder, file_id)

    # Check if the output file exists
    if not os.path.isfile(output_file):
        raise BadRequest("File not found for export")
    
    # Copy the file to the destination path
    try:
        shutil.copy(output_file, destination_path)
    except Exception as e:
        raise BadRequest(f"Error exporting file: {e}")

    return jsonify({"message": f"File exported successfully"}), 200


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
    if not basemap_id:
        raise BadRequest("basemap_id parameter is required")

    # TODO: fetch default basemap from config

    return jsonify({"message": "Loaded basemap {basemap_id}"}), 200 

@app.route('/basemaps', methods=['GET'])
def list_basemaps():
    basemaps = [
        {
            "id": "osm_standard",
            "name": "OpenStreetMap",
            "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
        },
        {
            "id": "esri_satellite",
            "name": "Satélite (Esri)",
            "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attribution": "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        },
        {
            "id": "open_topo",
            "name": "Topográfico (OpenTopo)",
            "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            "attribution": "Map data: &copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors, <a href='http://viewfinderpanoramas.org'>SRTM</a> | Map style: &copy; <a href='https://opentopomap.org'>OpenTopoMap</a> (<a href='https://creativecommons.org/licenses/by-sa/3.0/'>CC-BY-SA</a>)"
        },
        {
            "id": "carto_light",
            "name": "Cinza (Carto Light)",
            "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            "attribution": "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
        },
        {
            "id": "carto_dark",
            "name": "Escuro (Carto Dark)",
            "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            "attribution": "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
        }
    ]

    return jsonify({"basemaps": basemaps}), 200

@app.route('/basemaps/<basemap_id>', methods=['POST'])
def change_basemap(basemap_id):
    if not basemap_id:
        raise BadRequest("basemap_id is required")

    # TODO: change basemap

    return jsonify({"message": f"Basemap changed to {basemap_id}"}), 200


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

