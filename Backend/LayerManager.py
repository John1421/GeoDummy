from FileManager import FileManager
import os
import geopandas as gpd
import fiona
import fiona.transform
from fiona.errors import FionaValueError
import zipfile
from shapely.geometry import shape, mapping
import rioxarray
import shutil

file_manager = FileManager()

class LayerManager:
    def __init__(self, default_geopackage='layers.gpkg'):
        """
        Initializes the BasemapManager.

        - Checks if the default GeoPackage exists inside the FileManager layers directory.
        - Creates an empty GeoPackage if it does not exist.

        Parameters:
            file_manager (FileManager): Instance of FileManager to access directories.
            default_geopackage (str): File name for the default GeoPackage.
        """

        # Full path to the GeoPackage inside layers directory
        self.default_gpkg_path = os.path.join(file_manager.layers_dir, default_geopackage)

        # Ensure the default GeoPackage exists
        if not os.path.exists(self.default_gpkg_path):
            # Create an empty GeoDataFrame to initialize the new GeoPackage
            empty_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            empty_gdf.to_file(self.default_gpkg_path, driver='GPKG')


    #=====================================================================================
    #                               Layer Converters METHODS
    #=====================================================================================    

    def add_shapefile_zip(self, zip_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Extracts a zipped shapefile, validates required components,
        reads it using Fiona, reprojects features if needed,
        and writes it as a new layer in the default GeoPackage.

        Parameters:
            zip_path (str): Path to the ZIP shapefile.
            layer_name (str): Optional layer name for the GeoPackage.
            target_crs (str): CRS to convert into before writing.

        Returns:
            str: The layer name added to the GeoPackage.
        """

        if not os.path.isfile(zip_path):
            raise ValueError("Zip file does not exist.")

        required_exts = {".shp", ".shx", ".dbf"}

        extracted_files = []

        # 1. Extract ZIP
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(file_manager.temp_dir)
                extracted_files = zf.namelist()
        except Exception as e:
            raise ValueError(f"Error unzipping shapefile: {e}")
        
        #2. Delete zip file
        try:
            os.remove(zip_path)
        except Exception as e:
            raise ValueError(f"Failed to delete the zip file after extraction: {e}")

        # Locate the .shp file
        shp_files = [f for f in os.listdir(file_manager.temp_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            raise ValueError("No .shp file found inside the ZIP.")

        shp_name = shp_files[0]
        base_name = os.path.splitext(shp_name)[0]

        # 3. Validate required shapefile components
        extracted_files = set(os.listdir(file_manager.temp_dir))
        missing = [ext for ext in required_exts if f"{base_name}{ext}" not in extracted_files]

        if missing:
            raise ValueError(f"Missing shapefile component(s): {', '.join(missing)}")

        shp_path = os.path.join(file_manager.temp_dir, shp_name)

        # 4. Open with Fiona
        try:
            src = fiona.open(shp_path, 'r')
        except Exception as e:
            self.__cleanup_temp_files(file_manager.temp_dir, extracted_files)
            raise ValueError(f"Error opening shapefile with Fiona: {e}")

        # CRS from the shapefile
        src_crs = src.crs
        if not src_crs:
            src.close()

            # Cleanup extracted files
            self.__cleanup_temp_files(file_manager.temp_dir, extracted_files)

            raise ValueError("Shapefile CRS is missing (.prj not found or unreadable).")

        # Determine layer name
        if layer_name is None:
            layer_name = base_name

        # 4. Prepare GeoPackage layer schema
        schema = src.schema.copy()

        # 5. Reproject each feature if needed
        target_crs_fiona = fiona.crs.from_string(target_crs)
        needs_reproject = src_crs != target_crs_fiona

        # 6. Write into GeoPackage using Fiona
        try:
            with fiona.open(
                self.default_gpkg_path,
                mode="w",
                layer=layer_name,
                driver="GPKG",
                crs=target_crs_fiona,
                schema=schema
            ) as dst:

                for feature in src:
                    geom = feature["geometry"]

                    # Reproject geometry if needed
                    if needs_reproject:
                        try:
                            geom = fiona.transform.transform_geom(
                                src_crs,
                                target_crs_fiona,
                                geom,
                            )
                        except Exception as e:
                            raise ValueError(f"Geometry reprojection failed: {e}")

                    new_feature = {
                        "geometry": geom,
                        "properties": feature["properties"],
                    }

                    dst.write(new_feature)

        except Exception as e:
            raise ValueError(f"Error writing layer to GeoPackage: {e}")

        finally:
            src.close()
            self.__cleanup_temp_files(file_manager.temp_dir, extracted_files)

        return layer_name

    def add_geojson(self, geojson_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Reads a GeoJSON file, validates CRS, reprojects features if needed,
        and writes it as a new layer inside the default GeoPackage.

        Parameters:
            geojson_path (str): Path to the .geojson file.
            layer_name (str): Optional layer name inside the GeoPackage.
            target_crs (str): Target CRS for storage.

        Returns:
            str: The layer name added to the GeoPackage.
        """

        if not os.path.isfile(geojson_path):
            raise ValueError("GeoJSON file does not exist.")

        # Open the GeoJSON
        try:
            src = fiona.open(geojson_path, "r")
        except Exception as e:
            raise ValueError(f"Error opening GeoJSON: {e}")

        try:
            # Get CRS
            src_crs = src.crs
            if not src_crs:
                src.close()
                raise ValueError("GeoJSON has no CRS defined.")

            # Set layer name
            if layer_name is None:
                layer_name = os.path.splitext(os.path.basename(geojson_path))[0]

            # Determine target CRS
            target_crs_fiona = fiona.crs.from_string(target_crs)
            needs_reproject = src_crs != target_crs_fiona

            # Extract schema from GeoJSON
            schema = src.schema.copy()

            # Write to the GeoPackage
            with fiona.open(
                self.default_gpkg_path,
                mode="w",
                layer=layer_name,
                driver="GPKG",
                crs=target_crs_fiona,
                schema=schema
            ) as dst:

                for feature in src:
                    geom = feature["geometry"]

                    # Reproject if needed
                    if needs_reproject:
                        try:
                            geom = fiona.transform.transform_geom(
                                src_crs,
                                target_crs_fiona,
                                geom
                            )
                        except Exception as e:
                            raise ValueError(f"Geometry reprojection failed: {e}")

                    dst.write({
                        "geometry": geom,
                        "properties": feature["properties"]
                    })

        except Exception as e:
            raise ValueError(f"Error writing GeoJSON into GeoPackage: {e}")

        finally:
            # Ensure the source file is closed
            if 'src' in locals() and not src.closed:
                src.close()

        return layer_name

    def add_raster(self, raster_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Adds a raster (.tiff) file into a GeoPackage-compatible storage location.

        Parameters:
            raster_path (str): Path to the .tiff file.
            layer_name (str): Optional layer name for storage.

        Returns:
            str: The layer name added.
        """

        if not os.path.isfile(raster_path):
            raise ValueError("Raster file does not exist.")

        # Default layer name from file
        if layer_name is None:
            layer_name = os.path.splitext(os.path.basename(raster_path))[0]

        # Check if layer already exists (optional)
        if self.check_layer_name_exists(layer_name):
            raise ValueError(f"A raster layer with the name '{layer_name}' already exists.")

        try:
            if not self.__check_raster_system_coordinates(raster_path):
                try:
                    temp_path = self.__convert_raster_system_coordinates(raster_path)
                    file_manager.move_file(temp_path, file_manager.layers_dir)
                except Exception as e:
                    os.remove(raster_path)
                    raise ValueError(f"Failed convert raster system coordinates: {e}")    
            else:
                file_manager.move_file(raster_path, file_manager.layers_dir)
        except Exception as e:
            os.remove(raster_path)
            raise ValueError(f"Failed to add raster layer: {e}")

        return layer_name

    def add_gpkg_layers(self, geopackage_path, target_crs="EPSG:4326"):
        """
        Add all layers from an external GeoPackage into the application's
        default GeoPackage, with CRS normalization and name conflict checks.

        Parameters:
        geopackage_path (str): Path to the incoming .gpkg file.
        target_crs (str): CRS to convert vector layers to (default EPSG:4326)

        Raises:
            ValueError: If file does not exist, is invalid, or contains conflicting layer names.
        """

        incoming_layers = self.__retrieve_spatial_layers_from_incoming_gpkg(geopackage_path) 

        self.check_incoming_gpkg_layers_for_names_conflicts(incoming_layers)

        # Import each layer
        for layer_name in incoming_layers:
            try:
                gdf = gpd.read_file(geopackage_path, layer=layer_name)

                # Normalize CRS
                if gdf.crs is None:
                    raise ValueError(f"Layer '{layer_name}' has no CRS.")

                if gdf.crs.to_string() != target_crs:
                    gdf = gdf.to_crs(target_crs)

                # Append layer to DEFAULT GeoPackage
                gdf.to_file(
                    self.default_gpkg_path,
                    layer=layer_name,
                    driver="GPKG"
                )

            except Exception as e:
                raise ValueError(f"Failed to import layer '{layer_name}': {e}")

        return incoming_layers

    def export_geopackage_layer_to_geojson(self, layer_name, output_name=None):
        """
        Extracts a layer from the GeoPackage and saves it as a GeoJSON file.

        Parameters:
            layer_name (str): Name of the layer inside the GeoPackage.
            output_name (str): Optional output filename (without extension).
                            If None, defaults to layer_name.

        Returns:
            str: Path to the exported GeoJSON file.
        """

        # Determine output filename
        if output_name is None:
            output_name = layer_name

        geojson_path = os.path.join(
            file_manager.temp_dir,
            f"{output_name}.geojson"
        )

        # Open the layer in the GeoPackage
        try:
            with fiona.open(self.default_gpkg_path, layer=layer_name) as src:
                src_crs = src.crs
                schema = src.schema

                # Create GeoJSON file
                with fiona.open(
                    geojson_path,
                    mode='w',
                    driver="GeoJSON",
                    crs=src_crs,
                    schema=schema
                ) as dst:

                    # Copy features
                    for feature in src:
                        dst.write(feature)

        except Exception as e:
            raise ValueError(f"Error exporting layer '{layer_name}' to GeoJSON: {e}")

        return geojson_path
        
    def export_raster_layer(self, layer_name):
        """
        Locate a raster layer in file_manager.layers_dir using its layer name.

        Parameters:
            layer_name (str): Name of the raster layer (without extension).

        Returns:
            str: Full path to the raster file.

        Raises:
            ValueError: If the raster does not exist.
        """

        # Allowed raster extensions
        possible_exts = [".tif", ".tiff"]

        for ext in possible_exts:
            candidate_path = os.path.join(file_manager.layers_dir, layer_name + ext)
            if os.path.isfile(candidate_path):
                return candidate_path

        raise ValueError(f"Raster layer '{layer_name}' not found in layers directory.")

    def check_layer_name_exists(self, new_name):
        """
        Check if a layer with the given name exists in either:
        - the GeoPackage (vector layers)
        - the file_manager.layers_dir as a raster file (.tif or .tiff)

        Returns:
            bool: True if the layer exists, False otherwise.
        """

        exists = False

        # 1. Check vector layers in GPKG
        try:
            layers = fiona.listlayers(self.default_gpkg_path)
            if new_name in layers:
                exists = True
        except Exception:
            # GPKG may not exist yet or unreadable
            pass

        # 2. Check raster layers (.tif/.tiff)
        possible_exts = [".tif", ".tiff"]
        for ext in possible_exts:
            raster_path = os.path.join(file_manager.layers_dir, new_name + ext)
            if os.path.isfile(raster_path):
                exists = True
                break

        return exists
    
    def check_incoming_gpkg_layers_for_names_conflicts(self, new_layers):
        # Load existing GPkg layers + raster names
        existing_layers = set(fiona.listlayers(self.default_gpkg_path))
        existing_raster_layers = {
            os.path.splitext(f)[0]
            for f in os.listdir(file_manager.layers_dir)
            if f.lower().endswith((".tif", ".tiff"))
        }
        all_existing = existing_layers | existing_raster_layers

        # Check for name conflicts
        conflicts = [name for name in new_layers if name in all_existing]

        if conflicts:
            raise ValueError(
                "Cannot import GeoPackage. Conflicting layer names: "
                + ", ".join(conflicts)
            )     

    #=====================================================================================
    #                               HELPER METHODS
    #=====================================================================================    

    @staticmethod
    def __cleanup_temp_files(temp_dir, file_list):
        """
        Deletes files from the temporary directory.

        Parameters:
            file_list (list): List of filenames to delete.
            temp_dir (str): Path to the temporary directory.
        """
        for f in file_list:
            f_path = os.path.join(temp_dir, f)
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except Exception:
                    pass

    @staticmethod
    def __check_raster_system_coordinates(raster_path, target_crs="EPSG:4326"):
        try:
            # Read the GeoTIFF file
            with rioxarray.open_rasterio(raster_path) as raster:
                if raster.rio.crs is None:
                    raise ValueError("Raster has no CRS information.")
                else:
                    return raster.rio.crs.to_string() == target_crs
        except Exception as e:
            raise ValueError(f"Error checking tif CRS: {e}")    


    @staticmethod
    def __convert_raster_system_coordinates(raster_path,target_crs="EPSG:4326"):
        temp_path = f"very_complex_raster_name_temp.tiff"
        shutil.copy(raster_path, temp_path)
        try:
            with rioxarray.open_rasterio(temp_path) as raster:
                # Convert to target CRS
                raster_converted = raster.rio.reproject(target_crs)

                # Save the converted file back to the same path
                raster_converted.rio.to_raster(raster_path)

            os.remove(temp_path)    

            return raster_path
        except Exception as e:
            raise ValueError(f"Error converting tif CRS: {e}") 

    @staticmethod
    def __retrieve_spatial_layers_from_incoming_gpkg(new_geopackage_path): 
        try:
            all_layers = fiona.listlayers(new_geopackage_path)
        except Exception as e:
            raise ValueError(f"Invalid GeoPackage: {e}")

        if not all_layers:
            raise ValueError("GeoPackage contains no layers.")

        # 2. Filter only real spatial layers
        incoming_layers = []

        for layer in all_layers:
            try:
                with fiona.open(new_geopackage_path, layer=layer) as src:
                    geom = src.schema.get("geometry")
                    if geom in [None, "", "None"]:
                        # This is NOT a real vector layer → skip
                        continue
                    incoming_layers.append(layer)
            except FionaValueError:
                # Not a readable vector layer
                continue
            except Exception:
                continue

        if not incoming_layers:
            raise ValueError("No valid spatial layers found in GeoPackage.")
        
        return incoming_layers