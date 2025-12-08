from FileManager import FileManager
from LayerManager import LayerManager
import json
import os

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
    

    def add_script(self, script_id, parameters):
        """
        Adds a script entry if it doesn't already exist.
        """

        self.metadata["scripts"][script_id] = {
            "parameters": parameters
        }

        self._save_metadata()


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