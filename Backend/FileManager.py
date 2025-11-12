import geopandas as gpd
import shutil
import os

class FileManager:

    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif'}

    def __init__(self, input_dir='./input_layers', output_dir='./output'):
        self.input_dir = input_dir
        self.output_dir = output_dir

        # Create directories if they don't exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)


    def move_file(self, source_path, destination_path):
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)
        try:
            shutil.move(full_source_path, destination_path)
        except Exception as e:
            raise ValueError(f"Error moving file: {e}")
        return True

    def copy_file(self, source_path, destination_path):
        full_source_path = self.__validate_paths_and_file(source_path, destination_path)
        file_name = os.path.basename(source_path)
        destination_file = os.path.join(destination_path, file_name)

        try:
            shutil.copy(full_source_path, destination_file)
        except Exception as e:
            raise ValueError(f"Error copying file: {e}")
        return True


    def convert_to_geojson(self, file_path):
        file_name, file_name_ext = os.path.splitext(file_path)

        # If the file is already a GeoJSON, return the path
        if file_name_ext.lower() in ['.geojson', '.tif']:
            return file_path

        # Convert shapefile or geopackage to GeoJSON
        if file_name_ext.lower() in ['.shp', '.gpkg']:
            file_content = gpd.read_file(file_path)
            geojpeg_path = f"{file_name}.geojson"
            file_content.to_file(geojpeg_path, driver='GeoJSON')
            return geojpeg_path

        # If the file is of any other unsupported format, raise an error
        raise ValueError("Unsupported file format for conversion to GeoJSON.")

#=====================================================================================
#                               HELPER METHODS
#=====================================================================================

    @staticmethod
    def __validate_paths_and_file(source_path, destination_path):
        if not isinstance(source_path, str) or not os.path.isfile(source_path):
            raise ValueError("Invalid source file path")

        if not isinstance(destination_path, str) or not os.path.isdir(destination_path):
            raise ValueError("Invalid destination path")
        
        file_name = os.path.basename(source_path)
        hipothetical_destination_path = os.path.join(destination_path, file_name)

        if os.path.exists(hipothetical_destination_path):
            raise ValueError("A file with the same name already exists in the destination path")