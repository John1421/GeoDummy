from flask import Flask
from flask import request, jsonify
from werkzeug.exceptions import HTTPException, BadRequest
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

@app.route('/add_file', methods=['POST'])
def add_file():

    # TODO: Implement file upload

    return jsonify({"message": f"File added successfully"}), 200

@app.route('/export_file', methods=['POST'])
def export_file():

    # TODO: Implement file export

    return jsonify({"message": f"File exported successfully"}), 200


# Script Management Endpoints

@app.route('/add_script', methods=['POST'])
def add_script():

    # TODO: Implement script upload
    
    script_id = "script123"
    return jsonify({"message": f"Script added successfully", "script_id": script_id}), 200

@app.route('/remove_script', methods=['POST'])
def remove_script():
    script_id = request.args.get('script_id')
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: Implement script removal

    return jsonify({"message": f"Script {script_id} removed successfully"}), 200

@app.route('/list_scripts', methods=['GET'])
def list_scripts():

    # TODO: Implement script listing
    scripts = ["script001", "script002", "script003"]
    return jsonify({"message": f"List of scripts received", "scripts":scripts}), 200

@app.route('/script_metadata', methods=['GET'])
def script_metadata():
    script_id = request.args.get('script_id')
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: retrieve metadata

    return jsonify({"script_id": script_id, "output": "Metadata here"}), 200



# Script Execution Endpoints

@app.route('/run_script', methods=['POST'])
def run_script():
    data = request.get_json()
    script_id = data.get('script_id')
    if not script_id:
        raise BadRequest("script_id is required")
    parameters = data.get('parameters', {})

    # TODO: Implement script execution logic here

    return jsonify({"message": f"Running script {script_id}", "parameters": parameters}), 200

@app.route('/get_script_output', methods=['GET'])
def get_script_output():
    script_id = request.args.get('script_id')
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: retrieve output

    return jsonify({"script_id": script_id, "output": "Sample output here"}), 200

@app.route('/stop_script', methods=['POST'])
def stop_script():
    data = request.get_json()
    script_id = data.get('script_id')
    if not script_id:
        raise BadRequest("script_id is required")

    # TODO: stop running process

    return jsonify({"message": f"Script {script_id} stopped"}), 200

@app.route('/get_script_status', methods=['GET'])
def get_script_status():    
    script_id = request.args.get('script_id')
    if not script_id:
        raise BadRequest("script_id parameter is required")

    # TODO: check execution status

    return jsonify({"script_id": script_id, "status": "running"}), 200


# Map Interaction Endpoints

@app.route('/load_default_basemap', methods=['GET'])
def load_default_basemap():
    basemap = "Terrain.img"

    # TODO: fetch default basemap from config

    return jsonify({"message": "Default basemap loaded", "basemaps": basemap}), 200 

    

@app.route('/list_basemaps', methods=['GET'])
def list_basemaps():
    basemaps = ["Terrain", "Gray", "Satellite", "None"]

    # TODO: get all available basemaps

    return jsonify({"basemaps": basemaps}), 200

@app.route('/change_basemap', methods=['POST'])
def change_basemap():
    data = request.get_json()
    basemap_name = data.get('basemap_name')
    if not basemap_name:
        raise BadRequest("basemap_name is required")

    # TODO: change basemap

    return jsonify({"message": f"Basemap changed to {basemap_name}"}), 200


# Layer Management Endpoints

@app.route('/add_layer', methods=['POST'])
def add_layer():    
    layer_file = request.files['layer_file']
    if not layer_file:
        raise BadRequest("No layer file provided")
    name = request.form.get('layer_name', layer_file.filename)

    # TODO: process and add layer
    layer_id = "layer123"
    return jsonify({"message": f"Layer '{name}' added successfully", "layer_id": layer_id}), 200

app.route('/export_layer', methods=['POST'])
def export_layer():    
    data = request.get_json()
    layer_id = data.get('layer_id')
    if not layer_id:
        raise BadRequest("layer_id is required")

    # TODO: remove layer

    return jsonify({"message": f"Layer {layer_id} exported"}), 200

@app.route('/remove_layer', methods=['POST'])
def remove_layer():    
    data = request.get_json()
    layer_id = data.get('layer_id')
    if not layer_id:
        raise BadRequest("layer_id is required")

    # TODO: remove layer

    return jsonify({"message": f"Layer {layer_id} removed"}), 200

@app.route('/set_layer_priority', methods=['POST'])
def set_layer_priority():  
    data = request.get_json()
    layer_id = data.get('layer_id')
    if not layer_id:
        raise BadRequest("layer_id is required")
    priority = data.get('priority', [])
    if not priority:
        raise BadRequest("No priority provided")

    # TODO: set new layer priorities

    return jsonify({"message": "Layer priority updated", "New priority": priority}), 200


# Layer Information Endpoints

@app.route('/identify_layer_information', methods=['GET'])
def identify_layer_information():
    layer_id = request.args.get('layer_id')
    if not layer_id:
        raise BadRequest("layer_id parameter is required")

    # TODO: extract information

    return jsonify({"layer_id": layer_id, "info": {"geometry": "Polygon", "features": 124}}), 200

@app.route('/extract_data_from_layer_for_table_view', methods=['GET'])
def extract_data_from_layer_for_table_view():
    layer_id = request.args.get('layer_id')

    # TODO: extract data from file

    table_data = [{"name": "Feature 1", "type": "Polygon"}, {"name": "Feature 2", "type": "Line"}]
    return jsonify({"layer_id": layer_id, "table_data": table_data}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

