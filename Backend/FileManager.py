import geopandas as gpd
import shutil
import os

class FileManager:

    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif'}

    def __init__(self, input_dir='./input_layers', output_dir='./output'):
        """
        Constructor to initialize input and output directories.
        Creates directories if they do not already exist.
        
        Parameters:
            input_dir (str): Path for input files.
            output_dir (str): Path for output files.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir

        # Create directories if they don't exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    
    def move_file(self, source_path, destination_path):
        """
        Moves a file from source_path to destination_path.
        Raises an error if the source/destination is invalid or if the file already exists.

        Parameters:
            source_path (str): Full path to the source file. (e.g., ./input_layers/file.shp)
            destination_path (str): Directory where the file should be moved. (e.g., ./output)

        Returns:
            True if the move was successful.
        """
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)
        try:
            shutil.move(full_source_path, destination_path)
        except Exception as e:
            raise ValueError(f"Error moving file: {e}")
        return True


    def copy_file(self, source_path, destination_path):
        """
        Copies a file from source_path to destination_path.
        Raises an error if the source/destination is invalid or if a file with the same name exists in the destination.

        Parameters:
            source_path (str): Full path to the source file. (e.g., ./input_layers/file.shp)
            destination_path (str): Directory where the file should be copied. (e.g., ./output)

        Returns:
            True if the copy was successful.
        """
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)
        file_name = os.path.basename(source_path)
        destination_file = os.path.join(destination_path, file_name)

        try:
            shutil.copy(full_source_path, destination_file)
        except Exception as e:
            raise ValueError(f"Error copying file: {e}")
        return True


    def convert_to_geojson(self, file_path):
        import geopandas as gpd
import shutil
import os

class FileManager:

    # Allowed file extensions for processing
    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif'}

    def __init__(self, input_dir='./input_layers', output_dir='./output'):
        """
        Constructor to initialize input and output directories.
        Creates directories if they do not already exist.
        
        Parameters:
            input_dir (str): Path for input files.
            output_dir (str): Path for output files.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir

        # Create directories if they don't exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)


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
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)

        try:
            shutil.move(full_source_path, destination_path)
        except Exception as e:
            raise ValueError(f"Error moving file: {e}")
        return True


    def copy_file(self, source_path, destination_path):
        """
        Copies a file from source_path to destination_path.
        Raises an error if the source/destination is invalid or if a file with the same name exists in the destination.

        Parameters:
            source_path (str): Full path to the source file. (e.g., ./input_layers/file.shp)
            destination_path (str): Directory where the file should be copied. (e.g., ./output)

        Returns:
            True if the copy was successful.
        """
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)
        file_name = os.path.basename(source_path)
        destination_file = os.path.join(destination_path, file_name)

        try:
            shutil.copy(full_source_path, destination_file)
        except Exception as e:
            raise ValueError(f"Error copying file: {e}")
        return True


    def convert_to_geojson(self, file_path):
        """
        Converts supported file types (.shp, .gpkg) to GeoJSON format.
        If the file is already .geojson or .tif, returns the original path.

        Parameters:
            file_path (str): Path to the file to convert. (e.g., ./input_layers/file.shp)

        Returns:
            str: Path to the converted (or original) GeoJSON file. (e.g., ./input_layers/file.geojson)

        Raises:
            ValueError: If the file format is unsupported.
        """
        file_name, file_name_ext = os.path.splitext(file_path)

        # If already GeoJSON or GeoTIFF, no conversion needed
        if file_name_ext.lower() in ['.geojson', '.tif']:
            return file_path

        # Convert Shapefile or GeoPackage to GeoJSON
        if file_name_ext.lower() in ['.shp', '.gpkg']:
            file_content = gpd.read_file(file_path)
            geojpeg_path = f"{file_name}.geojson"
            file_content.to_file(geojpeg_path, driver='GeoJSON')
            return geojpeg_path

        # Unsupported file types raise an error
        raise ValueError("Unsupported file format for conversion to GeoJSON.")


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
            source_path (str): Path to the source file. (e.g., ./input_layers/file.shp)
            destination_path (str): Path to the destination directory. (e.g., ./output)

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

        file_name, file_name_ext = os.path.splitext(source_path)

        # If the file is already a GeoJSON, return the path
        if file_name_ext.lower() in ['.geojson', '.tif']:
            return source_path

        # Convert shapefile or geopackage to GeoJSON
        if file_name_ext.lower() in ['.shp', '.gpkg']:
            file_content = gpd.read_file(source_path)
            geojpeg_path = f"{file_name}.geojson"
            file_content.to_file(geojpeg_path, driver='GeoJSON')
            return geojpeg_path

        # If the file is of any other unsupported format, raise an error
        raise ValueError("Unsupported file format for conversion to GeoJSON.")

