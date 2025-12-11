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

    def run_script(self,script_path, script_id, parameters):
        # Load Python file dynamically
        spec = importlib.util.spec_from_file_location(script_id, script_path)
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise BadRequest(f"Error loading script: {str(e)}")
        

        
        # -------- LOGGING SETUP --------
        log_path = os.path.join(file_manager.temp_dir, f"log_{script_id}.txt")
        export = None

        buffer = io.StringIO()



        with redirect_stdout(buffer):
            try:
                # ----- LOAD SCRIPT DYNAMICALLY -----
                spec = importlib.util.spec_from_file_location(script_id, script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if not hasattr(module, "main"):
                    raise BadRequest("Script must define a function named 'main(params)'")
                else:
                    func = getattr(module, "main")

                args = self.__prepare_parameters_for_script(func,parameters)

                result = func(*args)

                # If result is a file path, move/copy it to temp_dir
                if isinstance(result, str) and os.path.isfile(result):
                    try:
                        _, ext = os.path.splitext(result)
                        filename = f"{script_id}_output{ext}"
                        saved_file_path = os.path.join(file_manager.temp_dir, filename)
                        shutil.move(result, saved_file_path)

                        export = self.__add_output_to_existing_layers_and_create_export_file(saved_file_path)
                    except Exception as e:
                        raise ValueError(f"Error saving script {script_id} result, error: {e}")
                    finally:
                        self.__clean_temp_layer_files(args)    
                else:
                    export = result

            except Exception as e:
                raise ValueError(f"Error executing script: {script_id}, error: {e}")
            
            finally:
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
    def __prepare_parameters_for_script(script_function, parameters):
        signature = inspect.signature(script_function)
        expected_arg_count = len(signature.parameters)

        arguments = list(parameters.values())

        if len(arguments) != expected_arg_count:
            raise BadRequest(
                f"main() expects {expected_arg_count} arguments, but client sent {len(arguments)}"
            )
        
        processed_arguments = []
        
        for arg in arguments:
            if isinstance(arg, str):
                # Replace string with get_layer result
                layer = layer_manager.get_layer_for_script(arg)
                if layer != None:
                    processed_arguments.append(layer)
                else:    
                    processed_arguments.append(arg)
            else:
                processed_arguments.append(arg)


        return processed_arguments
    
    @staticmethod
    def __clean_temp_layer_files(arguments):
        for arg in arguments:
             if os.path.isfile(arg):
                 os.remove(arg) 