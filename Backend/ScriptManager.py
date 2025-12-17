from FileManager import FileManager
from LayerManager import LayerManager
import json
import os
import importlib.util
from werkzeug.exceptions import BadRequest
import sys
import shutil
import zipfile
from contextlib import redirect_stdout
import io
import inspect

file_manager = FileManager()
layer_manager = LayerManager()

class ScriptManager:
    def __init__(self, scripts_metadata='scripts_metadata.json'):
        """
        Initializes the ScriptManager.

        - Checks if the script directory (from FileManager) exists.
            - Raises FileNotFoundError if the directory is missing.
        - Checks if the scripts metadata file exists inside that directory.
            - Creates an empty metadata JSON file if it does not exist.
        - Validates that for every script_id stored in metadata, a corresponding Python file exists in the scripts directory.

        Parameters:
            scripts_metadata (str): File name of the metadata JSON stored in the script directory.
        """
        # Make sure the directory exists
        if not os.path.isdir(file_manager.scripts_dir):
            raise FileNotFoundError(f"Script directory does not exist: {file_manager.scripts_dir}")

        # Build the full file path
        self.metadata_path = os.path.join(file_manager.scripts_dir, scripts_metadata)

        # If file does not exist, create it
        if not os.path.isfile(self.metadata_path):
            initial_structure = {"scripts": {}}
            with open(self.metadata_path, 'w') as f:
                json.dump(initial_structure, f, indent=4)

        # Load metadata
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)

        self._validate_script_files()

    def check_script_name_exists(self, script_id):
        """
        Checks whether a script with the given script_id already exists
        in the metadata JSON.

        Returns:
            bool: True if script exists, False otherwise.
        """
        return script_id in self.metadata.get("scripts", {})
    

    def add_script(self, script_id, parameters_form):
        """
        Adds a script entry if it doesn't already exist.
        """
        for key, value in parameters.items():
            try:
                parsed_value = json.loads(value)
                parameters[key] = parsed_value
            except (json.JSONDecodeError, TypeError):
                # Keep original string if not valid JSON
                pass

        parameters = {}
        for key in parameters_form:
            try:
                # Try to parse JSON values
                parameters[key] = json.loads(parameters_form[key])
            except (json.JSONDecodeError, TypeError):
                # Keep as string if not JSON
                parameters[key] = v[key]

        self._save_metadata()

    # TODO:
    # 1 - Construir um comando de execução controlado como: python script.py --params params.json
    # 2 - Lançar um processo de execução do script como subprocesso com utilizador de sistema não privilegiado e timeout de execução
    # 3 - Interpretar os outputs diferentes deste tipo de execução 
    # 4 - Devolver a API endpoint um objeto com:
    # {
    #   execution_id,
    #   estado final (success/failure/timeout/oom),
    #   paths dos outputs gerados,
    #   paths dos logs
    # }
    # 5 - Perguntar se a limpeza dos ficheiros temporários é para aqui ou para quem desenvolver o use case UC-B-14
    def run_script(self, script_path, script_id, execution_id, parameters):

        # Creating the execution_id folder within /temporary/scripts
        execution_folder = os.path.join(file_manager.execution_dir, str(execution_id))
        os.makedirs(execution_folder, exist_ok=True)

        # Copying script onto execution_folder
        script_copy_path = os.path.join(execution_folder, f"{script_id}.py")
        shutil.copy(script_path, script_copy_path)

        # Load Python file dynamically as a module
        spec = importlib.util.spec_from_file_location(script_id, script_copy_path)
        module = importlib.util.module_from_spec(spec)
        
        # Module execution attempt to catch loading errors
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise BadRequest(f"Error loading script: {str(e)}")
        
        # -------- EXECUTION_ID FOLDERS/FILES SETUP --------

        # Creating the inputs folder
        inputs_folder = os.path.join(execution_folder, "inputs")
        os.makedirs(inputs_folder, exist_ok=True)

        # Creating the outputs folder
        outputs_folder = os.path.join(execution_folder, "outputs")
        os.makedirs(outputs_folder, exist_ok=True)

        # Creating the log file
        log_path = os.path.join(execution_folder, f"log_{script_id}.txt")
    
        export = None

        buffer = io.StringIO()

        # Redirects all stdout outputs into the buffer for later logging
        with redirect_stdout(buffer):
            try:
                # ----- LOAD SCRIPT DYNAMICALLY -----

                # This bit of code is redundant - Esteves
                # spec = importlib.util.spec_from_file_location(script_id, script_path)
                # module = importlib.util.module_from_spec(spec)
                # spec.loader.exec_module(module)

                # Validate if script has "main" function
                if not hasattr(module, "main"):
                    raise BadRequest("Script must define a function named 'main(params)'")
                
                func = getattr(module, "main")

                # Prepare/Get required arguments for script execution and store in inputs folder   
                args = self.__prepare_parameters_for_script(func, parameters, inputs_folder)

                # Execute the main script function
                result = func(*args)

                # If result is a file path, move it to temporary/scripts/[execution_id]/outputs
                if isinstance(result, str) and os.path.isfile(result):
                    try:
                        _, ext = os.path.splitext(result)
                        output_filename = f"{execution_id}/{script_id}_output{ext}"
                        saved_file_path = os.path.join(outputs_folder, output_filename)

                        shutil.move(result, saved_file_path)

                        # Process the file based on the type
                        export = self.__add_output_to_existing_layers_and_create_export_file(saved_file_path)
                    except Exception as e:
                        raise ValueError(f"Error saving script {script_id} result, error: {e}")                           
                else:
                    # If the result is not a file, return as-is
                    export = result

            except Exception as e:
                raise ValueError(f"Error executing script: {script_id}, error: {e}")
            
            finally:
                # Remove remporary layer files
                self.__clean_temp_layer_files(args) 
                # Write to log the captured stdout
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(buffer.getvalue())

        return export    

    def _save_metadata(self):
        """Helper to persist metadata to disk."""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=4)

    def _validate_script_files(self):
        """
        Ensures that every script_id stored in metadata corresponds
        to an existing .py file inside the scripts directory.

        If a script file listed in metadata is missing, its entry
        is removed from metadata and changes are saved.
        """
        scripts = self.metadata.get("scripts", {})
        removed_scripts = []

        # Iterate over a copy of keys to avoid runtime error while deleting
        for script_id in list(scripts.keys()):
            script_file = os.path.join(file_manager.scripts_dir, f"{script_id}.py")
            if not os.path.isfile(script_file):
                removed_scripts.append(script_id)
                del self.metadata["scripts"][script_id]

        # Save updated metadata if any scripts were removed
        if removed_scripts:
            self._save_metadata()
            print(f"Removed missing scripts from metadata: {', '.join(removed_scripts)}")

    @staticmethod
    def __add_output_to_existing_layers_and_create_export_file(file_path):
        file_name, file_extension = os.path.splitext(file_path)
        layer_id = os.path.basename(file_name)

        match file_extension.lower():
            case ".shp":
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise BadRequest("Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj).")
            
            case ".zip":
                layer_manager.add_shapefile_zip(file_path,layer_id)
                os.remove(file_path)
                return layer_manager.export_geopackage_layer_to_geojson(layer_id)
            
            case ".geojson":        
                layer_manager.add_geojson(file_path,layer_id)
                os.remove(file_path)
                return layer_manager.export_geopackage_layer_to_geojson(layer_id)

            case ".tif" | ".tiff":
                layer_manager.add_raster(file_path,layer_id)
                return layer_manager.export_raster_layer(layer_id)
            
            case ".gpkg":
                new_layers = layer_manager.add_gpkg_layers(file_path)
                os.remove(file_path)
                zip_path = os.path.join(file_manager.temp_dir, f"{layer_id}_export.zip")

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for layer in new_layers:
                        # Export each layer from the default gpkg
                        exported_geojson = layer_manager.export_geopackage_layer_to_geojson(layer)
                        # Add it into zip
                        zipf.write(exported_geojson, arcname=f"{layer}.geojson")
                        # Optional cleanup
                        os.remove(exported_geojson)

                return zip_path
                
            case _: 
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise BadRequest("Fle extension not supported")
            
    @staticmethod
    def __prepare_parameters_for_script(script_function, parameters, execution_dir_input):
        # Get expected parameter count
        signature = inspect.signature(script_function)
        expected_arg_count = len(signature.parameters)

        arguments = list(parameters.values())

        # Validade argument count
        if len(arguments) != expected_arg_count:
            raise BadRequest(
                f"main() expects {expected_arg_count} arguments, but client sent {len(arguments)}"
            )
        
        # Validade execution_dir_input exists
        if not os.path.isdir(execution_dir_input):
            raise BadRequest(
                f"Couldn't locate folder to load input layers onto: {execution_dir_input}"
            )

        processed_arguments = [] 
        
        # Process each argument
        for arg in arguments:
            if isinstance(arg, str):
                # If string, attempt to replace it with get_layer result
                layer = layer_manager.get_layer_for_script(arg)

                if layer != None:
                    # Copy layer onto the execution_dir_input folder
                    layer_name = os.path.basename(layer)
                    layer_copy = os.path.join(execution_dir_input, layer_name)
                    shutil.copy(layer, layer_copy)

                    # Append layer_copy path if found
                    processed_arguments.append(layer_copy)
                else:    
                    # If layer not found, keep the original string
                    processed_arguments.append(arg)
            else:
                # If non-string argument, keep as-is
                processed_arguments.append(arg)
        
        return processed_arguments
    
    @staticmethod
    def __clean_temp_layer_files(arguments):
        for arg in arguments:
             if os.path.isfile(arg):
                 os.remove(arg) 