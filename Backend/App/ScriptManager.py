"""
Script execution and lifecycle management.

This module provides secure execution of user-defined Python scripts in
isolated environments, including input preparation, output normalization,
layer registration, logging, and metadata management.
"""

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

from werkzeug.exceptions import BadRequest, NotFound

from .FileManager import FileManager
from .LayerManager import LayerManager

file_manager = FileManager()
layer_manager = LayerManager()

class ScriptManager:
    """
    Manages user-provided Python scripts and their execution lifecycle.

    Responsibilities include script metadata persistence, validation, secure execution,
    input/output processing, and logging. Each script execution is sandboxed in its
    own temporary directory for isolation and concurrency safety.
    """

    MAX_SCRIPT_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_MIME_TYPES = {"text/x-python", "application/octet-stream", "text/x-python-script"}

    def __init__(self, scripts_metadata='scripts_metadata.json'):
        """
        Initialize the ScriptManager with metadata validation.

        :param scripts_metadata: File name of the metadata JSON stored in the script directory.
        :raises FileNotFoundError: If the script directory does not exist.
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
        Check whether a script with the given ID exists in metadata.

        :param script_id: Unique identifier for the script.
        :return: True if script exists, False otherwise.
        """

        return script_id in self.metadata.get("scripts", {})


    def add_script(self, script_id, metadata_form):
        """
        Add a new script entry to the metadata registry.

        :param script_id: Unique identifier for the script.
        :param metadata_form: Dictionary of metadata fields to store.
        """

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

    def run_script(self, script_path, script_id, execution_id, data):
        """
        Execute a Python script in an isolated, sandboxed environment.
        
        Creates an isolated execution environment with standardized folder structure,
        validates script integrity, prepares input parameters, executes the script as
        a subprocess, processes outputs, and captures execution logs.
        
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
        
        Supported Output Formats:
            - .geojson: Added to layer manager, exported as GeoJSON
            - .zip (shapefile): Extracted, added to layer manager, exported as GeoJSON
            - .tif/.tiff: Added as raster layer
            - .gpkg: All layers extracted, exported as zip of GeoJSON files
            - .shp: Rejected (must use .zip format)
        
        :param script_path: Absolute path to the Python script to execute.
        :param script_id: Unique identifier for the script.
        :param execution_id: Unique identifier for this execution instance.
        :param data: Dictionary of parameters to pass to the script.
        :return: Dictionary containing execution_id, status, layer_ids, metadatas, and log_path.
        :raises BadRequest: If script validation fails or unsupported output formats are produced.
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
        new_data = self.__prepare_parameters_for_script(data, inputs_folder)

        status = None

        # Execute the script as a subprocess. It will save outputs to the appropriate folder.
        try:
            script_copy_path_abs = os.path.abspath(script_copy_path)
            outputs_folder_abs = os.path.abspath(outputs_folder)
            data_str = json.dumps(new_data)

            result = subprocess.run(
                ["python", script_copy_path_abs, outputs_folder_abs, data_str],
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
        output_ids = []
        metadatas = []

        # Check for any files in outputs folder (layers).
        # 'Path([folder_path].glob("*"))' extracts all file paths within the folder_path
        output_files = list(Path(outputs_folder).glob("*"))

        for file_path in output_files:
            if file_path.is_file():
                filesize_bytes = os.path.getsize(file_path)
                if filesize_bytes > layer_manager.MAX_LAYER_FILE_SIZE:
                    raise BadRequest(
                        f"Output file {file_path.name} exceeds the maximum allowed size of {layer_manager.MAX_LAYER_FILE_SIZE} MB."
                        )

                layer_ids, metadata = self.__add_output_to_existing_layers(file_path)
                output_ids.extend(layer_ids)
                metadatas.extend(metadata)

        # If no files, fallback to stdout (simple value)
        if not output_ids and result is not None:
            stdout_value = result.stdout.strip()
            if stdout_value:
                result_value = stdout_value

        # Build the JSON object to return
        response = {
            "execution_id": execution_id,
            "status": status,
            "layer_ids": output_ids or [result_value], # fallback to stdout if no files
            "metadatas": metadata if output_ids else None,
            "log_path": log_path
        }

        # Remove temporary layer files
        self.__clean_temp_layer_files(new_data.get("layers", []))

        return response

    def _save_metadata(self):
        """
        Persist metadata to disk.
        """

        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=4)

    def _load_metadata(self):
        """
        Load metadata from disk.

        :return: Dictionary containing all script metadata.
        """

        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
        return self.metadata

    def get_metadata(self, script_id):
        """
        Retrieve metadata for a specific script.

        :param script_id: Unique identifier for the script.
        :return: Dictionary containing script metadata.
        """

        self.metadata = self._load_metadata()
        return self.metadata["scripts"][script_id]


    def _validate_script_files(self):
        """
        Ensure every script_id in metadata has a corresponding .py file.

        If a script file is missing, its entry is removed from metadata and
        changes are saved.
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
    def __add_output_to_existing_layers(file_path):
        """
        Process script output files and register them with the layer manager.

        :param file_path: Path to the output file to process.
        :return: Tuple of (list of layer_ids, list of metadata dicts).
        :raises BadRequest: If file format is not supported or is a shapefile without .zip.
        """

        file_name, file_extension = os.path.splitext(file_path)
        layer_id = os.path.basename(file_name)

        match file_extension.lower():
            case ".shp":
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise BadRequest("Please upload shapefiles as a .zip containing all necessary components (.shp, .shx, .dbf, optional .prj).")

            case ".zip":
                layer_id, metadata = layer_manager.add_shapefile_zip(file_path,file_name)

            case ".geojson":
                layer_id, metadata = layer_manager.add_geojson(file_path,file_name)

            case ".tif" | ".tiff":
                layer_id, metadata = layer_manager.add_raster(file_path,file_name)

            case ".gpkg":
                layer_id, metadata = layer_manager.add_gpkg_layers(file_path)

            case _:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise BadRequest("File extension not supported")


        if not isinstance(layer_id, list):
            layer_id = [layer_id]

        if not isinstance(metadata, list):
            metadata = [metadata]

        return layer_id, metadata

    def list_scripts(self):
        """
        List all registered scripts with their metadata.

        :return: Tuple of (list of script_ids, list of metadata dicts).
        :raises ValueError: If error occurs retrieving scripts.
        """

        try:
            script_metadatas = []
            script_ids = list(self.metadata.get("scripts", {}).keys())
            for script_id in script_ids:
                script_metadata = self.get_metadata(script_id)
                script_metadatas.append(script_metadata)
        except Exception as e:
            raise ValueError(f"Error retrieving scripts: {str(e)}")

        return script_ids, script_metadatas

    @staticmethod
    def __prepare_parameters_for_script(data, execution_dir_input):
        """
        Prepare input parameters for script execution by copying layer files.

        :param data: Dictionary containing layers and other parameters.
        :param execution_dir_input: Directory path where input files should be copied.
        :return: Dictionary with updated layer paths pointing to copied files.
        :raises BadRequest: If execution_dir_input doesn't exist.
        :raises NotFound: If a specified layer is not found.
        """

        # Validate execution_dir_input exists
        if not os.path.isdir(execution_dir_input):
            raise BadRequest(
                f"Couldn't locate folder to load input layers onto: {execution_dir_input}"
            )

        layers = data.get("layers", [])
        layers_paths = []

        # Process each argument
        for layer in layers:
            layer = layer_manager.get_layer_for_script(layer)

            if layer is not None:
                # Copy layer onto the execution_dir_input folder
                layer_name = os.path.basename(layer)
                layer_copy = os.path.join(execution_dir_input, layer_name)
                layer_abs = os.path.abspath(layer)
                layer_copy_abs = os.path.abspath(layer_copy)
                shutil.copy(layer_abs, layer_copy_abs)

                # Append layer_copy path if found
                layers_paths.append(layer_copy_abs)
            else:
                # Append original value if not a layer
                raise NotFound(f"Layer not found: {layer}"  )

        data["layers"] = layers_paths
        return data

    @staticmethod
    def __clean_temp_layer_files(layers):
        """
        Remove temporary layer files after script execution.

        :param layers: List of file paths to remove.
        """

        for layer in layers:
            if os.path.isfile(layer):
                os.remove(layer)

    @staticmethod
    def _validate_script_integrity(script_path):
        """
        Validate a Python script without executing it.
        
        Checks for syntax errors, ensures a function named 'main' exists,
        and verifies that 'main' is called under the 'if __name__ == "__main__"' guard.
        
        :param script_path: Absolute path to the Python script to validate.
        :raises BadRequest: If syntax errors exist, 'main' is missing, or 'main' is not
                           called under __main__ guard.
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
