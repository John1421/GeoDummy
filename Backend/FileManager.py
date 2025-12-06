import geopandas as gpd
import rioxarray
import shutil
import os


class FileManager:

    # Allowed file extensions for processing
    allowed_extensions = {'.geojson', '.shp', '.gpkg', '.tif', '.tiff'}

    def __init__(self, layers_dir='./input_layers', temp_dir='./temporary', scripts_dir='./scripts'):
        """
        Constructor to initialize layer and temporary directories.
        Creates directories if they do not already exist.
        
        Parameters:
            layers_dir (str): Path for layer files.
        """
        self.layers_dir = layers_dir
        self.temp_dir = temp_dir
        self.scripts_dir = scripts_dir

        # Create directories if they don't exist
        os.makedirs(self.layers_dir, exist_ok = True)
        os.makedirs(self.temp_dir, exist_ok = True)
        os.makedirs(self.temp_dir, exists_ok = True)


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


    def convert_to_geojson(self, file_path):
        """
        Converts supported file types (.shp, .gpkg) to GeoJSON format.
        If the file is already .geojson or .tif or .tiff, returns the original path.

        Parameters:
            file_path (str): Path to the file to convert. (e.g., ./layers_dir/file.shp)

        Returns:
            str: Path to the converted (or original) GeoJSON file. (e.g., ./layers_dir/file.geojson)

        Raises:
            ValueError: If the file format is unsupported.
        """
        file_name, file_name_ext = os.path.splitext(file_path)

        # If already GeoJSON or GeoTIFF, no conversion needed
        if file_name_ext.lower() in ['.geojson', '.tif', '.tiff']:
            return file_path

        # Convert Shapefile or GeoPackage to GeoJSON
        if file_name_ext.lower() in ['.shp', '.gpkg']:
            file_content = gpd.read_file(file_path)
            geojpeg_path = f"{file_name}.geojson"
            file_content.to_file(geojpeg_path, driver='GeoJSON')
            return geojpeg_path

        # Unsupported file types raise an error
        raise ValueError("Unsupported file format for conversion to GeoJSON.")
    

    def check_file_system_coordinates(self, file_path, target_crs="EPSG:4326"):
        """
        Checks if the GeoJSON/tif file is in the target coordinate reference system (CRS).

        Parameters:
            file_path (str): Path to the GeoJSON/tif file to check. (e.g., ./input_layers/file.geojson)
            target_crs (str): Target CRS in EPSG format. Default is "EPSG:4326".

        Returns:
            bool: True if the file is in the target CRS, False otherwise.

        Raises:
            ValueError: If the file format is unsupported or reading fails.
        """
        file_name, file_name_ext = os.path.splitext(file_path)

        if file_name_ext.lower() == '.geojson':
            try:
                # Read the GeoJSON file
                gdf = gpd.read_file(file_path)

                # Check if the CRS matches the target CRS
                return gdf.crs.to_string() == target_crs
            except Exception as e:
                raise ValueError(f"Error checking GeoJSON CRS: {e}")
            
        elif file_name_ext.lower() == '.tif' or file_name_ext.lower() == '.tiff':
            try:
                # Read the GeoTIFF file
                with rioxarray.open_rasterio(file_path) as raster:
                    if raster.rio.crs is None:
                        raise ValueError("Raster has no CRS information.")
                    else:
                        return raster.rio.crs.to_string() == target_crs
            except Exception as e:
                raise ValueError(f"Error checking tif CRS: {e}")    

            
        else:
            raise ValueError("CRS conversion is only supported for GeoJSON or tif files.")
    
    def convert_file_system_coordinates(self, file_path, target_crs="EPSG:4326"):
        """
        Converts the coordinate reference system (CRS) of a GeoJSON/tif file to the target CRS.

        Parameters:
            file_path (str): Path to the GeoJSON/tif file to convert. (e.g., ./input_layers/file.geojson)
            target_crs (str): Target CRS in EPSG format. Default is "EPSG:4326".

        Returns:
            str: Path to the converted GeoJSON file with the new CRS (The path stays the same). (e.g., ./input_layers/file.geojson)

        Raises:
            ValueError: If the file format is unsupported or conversion fails.
        """
        file_name, file_name_ext = os.path.splitext(file_path)

        # Ensure the file is a GeoJSON
        if file_name_ext.lower() == '.geojson':
            try:
                # Read the GeoJSON file
                gdf = gpd.read_file(file_path)

                # Convert to target CRS
                gdf = gdf.to_crs(target_crs)

                # Save the converted file back to the same path
                gdf.to_file(file_path, driver='GeoJSON')

                return file_path
            except Exception as e:
                raise ValueError(f"Error converting GeoJSON CRS: {e}")
            
        elif file_name_ext.lower() == '.tif' or file_name_ext.lower() == '.tiff':
            temp_path = f"{file_name}_temp{file_name_ext}"
            shutil.copy(file_path, temp_path)
            try:
                with rioxarray.open_rasterio(temp_path) as raster:
                    # Convert to target CRS
                    raster_converted = raster.rio.reproject(target_crs)

                    # Save the converted file back to the same path
                    raster_converted.rio.to_raster(file_path)

                os.remove(temp_path)    

                return file_path
            except Exception as e:
                raise ValueError(f"Error converting tif CRS: {e}")    
            
        else:
            raise ValueError("CRS conversion is only supported for GeoJSON or tif files.")


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


