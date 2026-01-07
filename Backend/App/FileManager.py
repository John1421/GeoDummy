import geopandas as gpd
import rioxarray
import shutil
import os


class FileManager:

    # Allowed file extensions for processing
    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}

    def __init__(self, layers_dir='./data/input_layers', temp_dir='./data/temporary', scripts_dir='./data/scripts', logs_dir='./logs'):
        """
        Constructor to initialize layer and temporary directories.
        Creates directories if they do not already exist.
        
        Parameters:
            layers_dir (str): Path for layer files.
            temporary (str): Path for temporary files.
            scripts (str): Path for script tools
        """
        self.layers_dir = layers_dir
        self.temp_dir = temp_dir
        self.scripts_dir = scripts_dir
        self.execution_dir = os.path.join(self.temp_dir, "scripts")
        self.raster_cache_dir = os.path.join(self.temp_dir, "raster_cache")
        self.logs_dir = logs_dir

        # Create directories if they don't exist
        os.makedirs(self.layers_dir, exist_ok = True)
        os.makedirs(self.temp_dir, exist_ok = True)
        os.makedirs(self.scripts_dir, exist_ok = True)
        os.makedirs(self.execution_dir, exist_ok = True)
        os.makedirs(self.raster_cache_dir, exist_ok = True)
        os.makedirs(self.logs_dir, exist_ok = True)


    def move_file(self, source_path, destination_path):
        """
        Moves a file from source_path to destination_path.
        Raises an error if the source/destination is invalid or if the file already exists.

        Parameters:
            source_path (str): Full path to the source file.
            destination_path (str): Directory where the file should be moved.

        Returns:
            True if the move was successful.
        """
        self.__validate_paths_and_file(source_path, destination_path)

        try:
            shutil.move(source_path, destination_path)
        except Exception as e:
            raise ValueError(f"Error moving file: {e}")
        return True


    def copy_file(self, source_path, destination_path):
        """
        Copies a file from source_path to destination_path.
        Raises an error if the source/destination is invalid or if a file with the same name exists in the destination.

        Parameters:
            source_path (str): Full path to the source file. (e.g., ./temp/file.shp)
            destination_path (str): Directory where the file should be copied. (e.g., ./layers_dir)

        Returns:
            True if the copy was successful.
        """
        self.__validate_paths_and_file(source_path, destination_path)

        file_name = os.path.basename(source_path)
        destination_file = os.path.join(destination_path, file_name)

        try:
            shutil.copy(source_path, destination_file)
        except Exception as e:
            raise ValueError(f"Error copying file: {e}")
        return True

    #=====================================================================================
    #                               HELPER METHODS
    #=====================================================================================

    @staticmethod
    def __validate_paths_and_file(source_path, destination_path):
        """
        Validates source file path and destination directory.
        Ensures the source exists, the destination is a valid directory,
        and that no file with the same name exists in the destination.

        Parameters:
            source_path (str): Path to the source file. (e.g., ./temp_dir/file.shp)
            destination_path (str): Path to the destination directory. (e.g., ./layers_dir)

        Raises:
            ValueError: If the source or destination is invalid, or if a conflicting file exists.
        """

        # Validate source path
        if not isinstance(source_path, str) or not os.path.isfile(source_path):
            raise ValueError("Invalid source file path")

        # Validate destination path
        if not isinstance(destination_path, str) or not os.path.isdir(destination_path):
            raise ValueError("Invalid destination path")
        
        # Check for existing file in destination
        file_name = os.path.basename(source_path)
        hipothetical_destination_path = os.path.join(destination_path, file_name)

        if os.path.exists(hipothetical_destination_path):
            raise ValueError("A file with the same name already exists in the destination path")

        return True


