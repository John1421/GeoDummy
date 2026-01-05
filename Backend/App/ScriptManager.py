from .FileManager import FileManager
from .LayerManager import LayerManager
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
import subprocess
import ast
from pathlib import Path

file_manager = FileManager()
layer_manager = LayerManager()

class ScriptManager:

    MAX_SCRIPT_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_MIME_TYPES = {"text/x-python", "application/octet-stream"}

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
    

    def add_script(self, script_id, metadata_form):
        parsed_metadata = {}

        for key, value in metadata_form.items():
            try:
                parsed_metadata[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                parsed_metadata[key] = value
        
        if "scripts" not in self.metadata:
            self.metadata["scripts"] = {}
        
        self.metadata["scripts"][script_id] = parsed_metadata
        self._save_metadata()

    def run_script(self, script_path, script_id, execution_id, parameters):
        """
        Executes a Python script in an isolated, sandboxed environment with 
        comprehensive input/output handling, validation, and logging.
        
        This method orchestrates the complete lifecycle of script execution:
        - Creates an isolated execution environment with standardized folder structure
        - Validates script integrity (syntax, structure, entry point)
        - Prepares and serializes input parameters, resolving layer references to files
        - Executes the script as a subprocess with timeout protection
        - Processes and normalizes output files (GeoJSON, shapefiles, rasters, etc.)
        - Registers outputs with the layer manager for downstream usage
        - Captures all execution logs for debugging and audit purposes
        
        Execution Environment Structure:
            /temporary/scripts/{execution_id}/
            ├── {script_id}.py          # Isolated copy of the script
            ├── inputs/                  # Input files and params.json
            ├── outputs/                 # Script-generated output files
            └── log_{script_id}.txt     # Execution logs (stdout/stderr)
        
        Script Requirements:
            - Must define a function named 'main(params)'
            - Must call main() within 'if __name__ == "__main__":' guard
            - Must be syntactically valid Python
            - Should save outputs to the provided outputs_folder path
            - Should read parameters from the provided params.json path
        
        Parameter Processing:
            - String parameters: Checked against layer manager
                * If layer exists: Layer file copied to inputs/, path provided to script
                * If not a layer: Original string value passed through
            - Non-string parameters: Passed through unchanged (numbers, booleans, etc.)
            - All parameters serialized to inputs/params.json for script consumption
        
        Output Processing:
            Supported output formats (automatically normalized):
            - .geojson: Added to layer manager, exported as standardized GeoJSON
            - .zip (shapefile): Extracted, added to layer manager, exported as GeoJSON
            - .tif/.tiff: Added as raster layer, exported for download
            - .gpkg: All layers extracted, exported as zip of GeoJSON files
            - .shp: Rejected (must use .zip format)
            
            If no output files produced, stdout is captured as the result value.
        
        Args:
            script_path (str): Absolute path to the Python script to execute.
            script_id (str): Unique identifier for the script (used in naming).
            execution_id (str|int): Unique identifier for this execution instance.
                Used to create an isolated execution folder.
            parameters (dict): Dictionary of parameters to pass to the script.
                Keys are parameter names, values can be:
                - str: Treated as potential layer IDs or literal strings
                - int, float, bool: Passed through as-is
                - Other JSON-serializable types
        
        Returns:
            dict: Execution result containing:
                {
                    "execution_id": str|int,  # Echo of input execution_id
                    "status": str,             # "success", "timeout", or "failure"
                    "outputs": list,           # Paths to processed output files, or
                                            # [stdout_value] if no files produced
                    "log_path": str           # Path to execution log file
                }
        
        Raises:
            BadRequest: If script validation fails (syntax errors, missing main(),
                improper structure), if parameter processing encounters issues,
                or if unsupported output file formats are produced.
            
            Note: Exceptions during script execution are caught and returned as
            status="failure" rather than propagated.
        
        Execution Constraints:
            - Timeout: 30 seconds (scripts exceeding this are killed)
            - Working directory: Set to execution_folder during subprocess execution
            - Environment: Inherits parent process environment
        
        Side Effects:
            - Creates execution folder and subdirectories in file_manager.execution_dir
            - Copies script file to execution folder
            - Copies layer files to inputs/ folder (if parameters reference layers)
            - Writes params.json to inputs/ folder
            - Writes log file to execution folder
            - Registers output layers with layer_manager
            - Removes temporary input layer files after execution
            - May remove temporary output files after processing (format-dependent)
        
        Example:
            >>> response = executor.run_script(
            ...     script_path="/scripts/buffer_analysis.py",
            ...     script_id="buffer_001",
            ...     execution_id="exec_12345",
            ...     parameters={"input_layer": "roads_2024", "distance": 100}
            ... )
            >>> print(response)
            {
                "execution_id": "exec_12345",
                "status": "success",
                "outputs": ["/exports/buffered_roads.geojson"],
                "log_path": "/temporary/scripts/exec_12345/log_buffer_001.txt"
            }
        
        Thread Safety:
            Each execution uses a unique execution_id, making concurrent executions
            safe as long as execution_id values are unique.
        """


        # -------- EXECUTION_ID FOLDERS/FILES SETUP --------

        # Creating the execution_id folder within /temporary/scripts
        execution_folder = os.path.join(file_manager.execution_dir, str(execution_id))
        os.makedirs(execution_folder, exist_ok=True)

        # Copying script onto execution_folder
        script_copy_path = os.path.join(execution_folder, f"{script_id}.py")
        shutil.copy(script_path, script_copy_path)

        # Check for syntax errors, "main" function declaration and its call through __main__
        self._validate_script_integrity(script_copy_path)

        # Creating the inputs folder
        inputs_folder = os.path.join(execution_folder, "inputs")
        os.makedirs(inputs_folder, exist_ok=True)

        # Creating the outputs folder
        outputs_folder = os.path.join(execution_folder, "outputs")
        os.makedirs(outputs_folder, exist_ok=True)

        # Creating the log file
        log_path = os.path.join(execution_folder, f"log_{script_id}.txt")
    
        # ----- SCRIPT PREPARATION AND EXECUTION -----

        # Prepare/Get required arguments for script execution and store in inputs folder   
        args = self.__prepare_parameters_for_script(parameters, inputs_folder)

        # Write arguments in inputs folder (paths for files and values for others) int oan input json
        params_json = os.path.join(inputs_folder, "params.json")
        with open(params_json, "w") as f:
            json.dump(args, f)

        status = None

        # Execute the script as a subprocess. It will save outputs to the appropriate folder.
        try:
            print("="*20)
            print(f"Executing script {script_id} with execution ID {execution_id}")
            print(f"Script path: {script_copy_path}")
            print(f"Inputs folder: {inputs_folder}")
            print(f"Outputs folder: {outputs_folder}")
            print(f"Parameters JSON: {params_json}")
            print("="*20)
            result = subprocess.run(
                ["python", script_copy_path, outputs_folder, params_json],
                cwd=execution_folder,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            status = "success"
        except subprocess.TimeoutExpired:
            status = "timeout"
            result = None  # optional
        except subprocess.CalledProcessError as e:
            status = "failure"
            result = e  # contains stdout/stderr


        # ----- LOGGING AND OUTPUT HANDLING -----

        # Write all prints and errors that occured during execution to the log file
        with open(log_path, "w", encoding="utf-8") as f:
            if result is not None:
                f.write(result.stdout)
                f.write(result.stderr)
            else:
                f.write("Script Timeout.")

        # ---- Handle outputs ----
        result_value = None
        output_file_paths = []

        # Check for any files in outputs folder (layers). 'Path([folder_path].glob("*"))' extracts all file paths within the folder_path
        output_files = list(Path(outputs_folder).glob("*"))

        for file_path in output_files:
            if file_path.is_file():
                filesize_bytes = os.path.getsize(file_path)
                if filesize_bytes > layer_manager.MAX_LAYER_FILE_SIZE:
                    raise BadRequest(f"Output file {file_path.name} exceeds the maximum allowed size of {layer_manager.MAX_LAYER_FILE_SIZE} MB.")
                saved_file = self.__add_output_to_existing_layers_and_create_export_file(file_path)
                output_file_paths.append(saved_file)
                
        # If no files, fallback to stdout (simple value)
        if not output_file_paths and result is not None:
            stdout_value = result.stdout.strip()
            if stdout_value:
                result_value = stdout_value

        # Build the JSON object to return
        response = {
            "execution_id": execution_id,
            "status": status,
            "outputs": output_file_paths or [result_value], # fallback to stdout if no files
            "log_path": log_path
        }

        # Remove temporary layer files
        self.__clean_temp_layer_files(args) 

        return response    

    def _save_metadata(self):
        """Helper to persist metadata to disk."""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=4)
            
    def _load_metadata(self):
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
        return self.metadata
    
    def get_metadata(self, script_id):
        self.metadata = self._load_metadata()
        return self.metadata["scripts"][script_id]
        
    
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
    def __prepare_parameters_for_script(parameters, execution_dir_input, expected_arg_count=None):
        """
        Prepares input parameters for script execution.

        - Validates parameter count if expected_arg_count is provided.
        - Copies any string arguments that correspond to layers into the execution_dir_input.
        - Returns a list of processed arguments ready to be passed to the script.
        """

        arguments = list(parameters.values())

        # Validate argument count if provided
        if expected_arg_count is not None and len(arguments) != expected_arg_count:
            raise BadRequest(
                f"main() expects {expected_arg_count} arguments, but client sent {len(arguments)}"
            )

        # Validate execution_dir_input exists
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

                if layer is not None:
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

    @staticmethod
    def _validate_script_integrity(script_path):
        
        """
        Validates the integrity of a Python script without executing it.

        - Checks for syntax errors.
        - Ensures a function named 'main' exists.
        - Verifies that 'main' is called under the 
        `if __name__ == "__main__"` guard.

        :param script_path: Absolute path to the Python script to validate.
        :raises BadRequest: If syntax errors exist, 'main' is missing,
                            or 'main' is not called under __main__ guard.
        """

        # Syntax check
        result = subprocess.run(
            ["python", "-m", "py_compile", script_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise BadRequest(result.stderr)

        # Check for main() definition
        with open(script_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=script_path)

        if not any(
            isinstance(node, ast.FunctionDef) and node.name == "main"
            for node in ast.walk(tree)
        ):
            raise BadRequest("Script must define a function named 'main(params)'")
        
        # Check for main() call under __main__ guard
        main_called = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                # Detect if __name__ == "__main__"
                if (isinstance(test, ast.Compare) and
                    isinstance(test.left, ast.Name) and
                    test.left.id == "__name__" and
                    isinstance(test.comparators[0], ast.Constant) and
                    test.comparators[0].value == "__main__"):
                    # Check if main() is called inside this block
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and getattr(child.func, "id", None) == "main":
                            main_called = True
                            break
        if not main_called:
            raise BadRequest("'main(params)' function is not called under '__main__' guard")