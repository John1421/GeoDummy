"""
File manager module.

Provides utilities for validating, moving, and copying geospatial
files while managing application directories.
"""

import shutil
import os


class FileManager:
    """
    Manages file system operations for layer, temporary, script,
    raster cache, and log directories.
    """

    # Allowed file extensions for processing
    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}

    def __init__(
            self,
            layers_dir='./data/input_layers',
            temp_dir='./data/temporary',
            scripts_dir='./data/scripts',
            logs_dir='./logs'
        ):
        """
        Initialize directory structure for file management.

        :param layers_dir: Path for layer files.
        :param temp_dir: Path for temporary files.
        :param scripts_dir: Path for script tools.
        :param logs_dir: Path for log files.
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
        Move a file to a destination directory.

        :param source_path: Full path to the source file.
        :param destination_path: Target directory.
        :return: True if the move was successful.
        :raises ValueError: If validation or move fails.
        """

        self.__validate_paths_and_file(source_path, destination_path)

        try:
            shutil.move(source_path, destination_path)
        except Exception as e:
            raise ValueError(f"Error moving file: {e}") from e
        return True


    def copy_file(self, source_path, destination_path):
        """
        Copy a file to a destination directory.

        :param source_path: Full path to the source file.
        :param destination_path: Target directory.
        :return: True if the copy was successful.
        :raises ValueError: If validation or copy fails.
        """

        self.__validate_paths_and_file(source_path, destination_path)

        file_name = os.path.basename(source_path)
        destination_file = os.path.join(destination_path, file_name)

        try:
            shutil.copy(source_path, destination_file)
        except Exception as e:
            raise ValueError(f"Error copying file: {e}") from e
        return True

    #=====================================================================================
    #                               HELPER METHODS
    #=====================================================================================

    @staticmethod
    def __validate_paths_and_file(source_path, destination_path):
        """
        Validate source file and destination directory.

        :param source_path: Path to the source file.
        :param destination_path: Path to the destination directory.
        :return: True if validation succeeds.
        :raises ValueError: If validation fails.
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
