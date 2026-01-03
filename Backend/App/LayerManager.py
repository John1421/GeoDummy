from .FileManager import FileManager
import os
import geopandas as gpd
import fiona
from fiona.errors import FionaValueError
import zipfile
from shapely.geometry import shape, mapping
import rioxarray
import shutil
import rasterio
from rasterio.warp import transform_bounds
import uuid
import json
from werkzeug.exceptions import NotFound
import math

file_manager = FileManager()

class LayerManager:
    MAX_LAYER_FILE_SIZE = 1000 * 1024 * 1024 # 1000 MB
    def __init__(self):
        # Default GeoPackage path for vector layers
        self.default_gpkg_path = os.path.join(file_manager.layers_dir, "default.gpkg")
        
        # Supported layer formats
        supported_ext = {'.gpkg', '.tif', '.tiff'}

        try:
            all_files = set(os.listdir(file_manager.layers_dir))
        except FileNotFoundError:
            return
        
        for filename in list(all_files):
            layer_id, ext = os.path.splitext(filename)
            ext = ext.lower()

            # --- Check 1: Layer File missing Metadata ---
            if ext in supported_ext:
                expected_meta = f"{layer_id}_metadata.json"

                if expected_meta not in all_files:
                    try:
                        os.remove(os.path.join(file_manager.layers_dir, filename))
                        print(f"Integrity: Deleted orphan layer '{filename}'")
                    except OSError as e:
                        print(f"Error deleting orphan layer: {e}")
            
            # --- Check 2: Metadata File missing Layer ---
            elif filename.endswith('_metadata.json'):
                # Extract ID: "my_layer_metadata.json" -> "my_layer"
                # len("_metadata.json") is 14
                meta_layer_id = filename[:-14] 
                
                layer_found = False
                for sext in supported_ext:
                    candidate = f"{meta_layer_id}{sext}"
                    if candidate in all_files:
                        layer_found = True
                        break

                if not layer_found:
                    try:
                        os.remove(os.path.join(file_manager.layers_dir, filename))
                        print(f"Integrity: Deleted orphan metadata '{filename}'")
                    except OSError as e:
                        print(f"Error deleting orphan metadata: {e}")


    #=====================================================================================
    #                               Layer Converters METHODS
    #=====================================================================================    

    def add_shapefile_zip(self, zip_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Import a zipped ESRI Shapefile into the system by converting it into a
        GeoPackage layer.

        Parameters:
            zip_path(str): Absolute path to the ZIP file containing the shapefile components.
            layer_name(str): Name of the layer to be created in the GeoPackage. If not provided,
            target_crs(str): Target coordinate reference system to reproject the data to. Defaults to "EPSG:4326".

        Returns:
            tuple[new_gpkg_id(str), metadata(str)]:
            The UUID of the newly created GeoPackage.
            Metadata extracted from the GeoPackage.
        """
        # 1. Extract ZIP
        temp_dir = os.path.join(file_manager.temp_dir, "shp_extracted")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
        except Exception as e:
            os.remove(zip_path)
            raise ValueError(f"Error unzipping shapefile: {e}")

        # 2. Delete zip file
        try:
            os.remove(zip_path)
        except Exception as e:
            raise ValueError(f"Failed to delete the zip file after extraction: {e}")

        # 3. Locate the .shp file
        shp_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(temp_dir)
            raise ValueError("No .shp file found inside the ZIP.")

        shp_path = os.path.join(temp_dir, shp_files[0])

        # 4. Read shapefile with GeoPandas
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            shutil.rmtree(temp_dir)
            raise ValueError(f"Error reading shapefile with GeoPandas: {e}")

        try:
            # 5. Check CRS
            if gdf.crs is None:
                shutil.rmtree(temp_dir)
                raise ValueError("Shapefile has no CRS defined (.prj missing or unreadable).")

            # 6. Reproject if needed
            original_crs = gdf.crs.to_string()
            if original_crs != target_crs:
                gdf = gdf.to_crs(target_crs)


            # 7. Determine layer name
            if layer_name is None:
                layer_name = os.path.splitext(shp_files[0])[0]

            # 8. Create unique gpkg ids
            new_gpkg_id = str(uuid.uuid4())
            new_gpkg_path = os.path.join(file_manager.temp_dir, f"{new_gpkg_id}.gpkg")


            # 9. Write to default GeoPackage
            gdf.to_file(
                new_gpkg_path,
                layer=layer_name,
                driver="GPKG"
            )

            # 10. Cleanup extracted files
            shutil.rmtree(temp_dir)


            metadata = self.__get_gpkg_metadata(new_gpkg_path, original_crs)
            self.__move_to_permanent(new_gpkg_path, new_gpkg_id, metadata)
        except Exception as e:
            raise ValueError(f"Error writing shapefile into GeoPackage: {e}")    

        return new_gpkg_id, metadata

    def add_geojson(self, geojson_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Reads a GeoJSON file, validates CRS, reprojects features if needed,
        and writes it as a new layer inside the default GeoPackage.

        Parameters:
            geojson_path (str): Path to the .geojson file.
            layer_name (str): Optional layer name inside the GeoPackage.
            target_crs (str): Target CRS for storage.

        Returns:
            tuple[new_gpkg_id(str), metadata(str)]:
            The UUID of the newly created GeoPackage.
            Metadata extracted from the GeoPackage.
        """

        if not os.path.isfile(geojson_path):
            raise ValueError("GeoJSON file does not exist.")

        try:
            # Read source layer
            gdf = gpd.read_file(geojson_path)  # can specify layer= if from a GeoPackage

            # Check CRS
            if gdf.crs is None:
                raise ValueError("Source layer has no CRS")

            # Reproject if needed
            original_crs = gdf.crs.to_string()
            if original_crs != target_crs:
                gdf = gdf.to_crs(target_crs)

            # Create unique gpkg ids
            new_gpkg_id = str(uuid.uuid4())
            new_gpkg_path = os.path.join(file_manager.temp_dir, f"{new_gpkg_id}.gpkg")


            # Write to default GeoPackage
            gdf.to_file(
                new_gpkg_path,
                layer=layer_name,
                driver="GPKG"
            )

            os.remove(geojson_path)

            metadata = self.__get_gpkg_metadata(new_gpkg_path, original_crs)
            self.__move_to_permanent(new_gpkg_path, new_gpkg_id, metadata)
        except Exception as e:
            raise ValueError(f"Error writing GeoJSON into GeoPackage: {e}")

        return new_gpkg_id, metadata

    def add_raster(self, raster_path, layer_name=None, target_crs="EPSG:4326"):
        """
        Adds a raster (.tiff) file into a storage location.

        Parameters:
            raster_path (str): Path to the .tiff file.
            layer_name (str): Optional layer name for storage.

        Returns:
            tuple[raster_name(str), metadata(str)]:
            The name of the raster.
            Metadata extracted from the raster.
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
            original_crs = self.__check_raster_system_coordinates(raster_path)
            if original_crs != target_crs:
                try:
                    temp_path = self.__convert_raster_system_coordinates(raster_path)
                    metadata = self.__get_raster_metadata(temp_path, original_crs)
                    self.__move_to_permanent(temp_path, layer_name, metadata)
                except Exception as e:
                    os.remove(raster_path)
                    raise ValueError(f"Failed convert raster system coordinates: {e}")    
            else:
                metadata = self.__get_raster_metadata(raster_path, target_crs)
                self.__move_to_permanent(raster_path, layer_name, metadata)
        except Exception as e:
            os.remove(raster_path)
            raise ValueError(f"Failed to add raster layer: {e}")

        return layer_name, metadata

    def add_gpkg_layers(self, geopackage_path, target_crs="EPSG:4326"):
        """
        Add all layers from an external GeoPackage into the application's
        default GeoPackage, with CRS normalization and name conflict checks.

        Parameters:
            geopackage_path (str): Path to the incoming .gpkg file.
            target_crs (str): CRS to convert vector layers to (default EPSG:4326)

        Returns
        tuple[list(new_gpkg_id(str)), list(metadata(str))]:
            The UUID of the newly created GeoPackages.
            Metadata extracted from the GeoPackages.

        Raises:
            ValueError: If file does not exist, is invalid, or contains conflicting layer names.
        """

        incoming_layers = self.__retrieve_spatial_layers_from_incoming_gpkg(geopackage_path)

        all_metadata = []
        all_gpkg_ids = [] 

        # Import each layer
        for layer_name in incoming_layers:
            try:
                gdf = gpd.read_file(geopackage_path, layer=layer_name)

                # Normalize CRS
                if gdf.crs is None:
                    raise ValueError(f"Layer '{layer_name}' has no CRS.")

                original_crs = gdf.crs.to_string()
                if original_crs != target_crs:
                    gdf = gdf.to_crs(target_crs)

                # Create unique gpkg ids
                new_gpkg_id = str(uuid.uuid4())
                new_gpkg_path = os.path.join(file_manager.temp_dir, f"{new_gpkg_id}.gpkg")


                # Write to default GeoPackage
                gdf.to_file(
                    new_gpkg_path,
                    layer=layer_name,
                    driver="GPKG"
                )

                metadata = self.__get_gpkg_metadata(new_gpkg_path, original_crs)
                self.__move_to_permanent(new_gpkg_path, new_gpkg_id, metadata)
                all_gpkg_ids.append(new_gpkg_id)
                all_metadata.append(metadata)
            except Exception as e:
                raise ValueError(f"Failed to import layer '{layer_name}': {e}")

        os.remove(geopackage_path)

        return all_gpkg_ids, all_metadata

    def export_geopackage_layer_to_geojson(self, layer_id):
        """
        Extracts a layer from a GeoPackage and saves it as a GeoJSON file.

        Parameters:
            layer_id(str): The id of the GeoPackage.

        Returns:
            str: Path to the exported GeoJSON file.
        """
        export_dir = os.path.join(file_manager.temp_dir, "export")

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

        # Clean export directory (delete existing files)
        for filename in os.listdir(export_dir):
            file_path = os.path.join(export_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        geojson_path = os.path.join(export_dir, f"{layer_id}.geojson")

        gpkg_path = os.path.join(file_manager.layers_dir, f"{layer_id}.gpkg")

        # Open the layer in the GeoPackage
        try:
            layers = fiona.listlayers(gpkg_path)
            if not layers:
                raise ValueError("No layers found in the GeoPackage.")

            layer_name = layers[0]

            # Open the only layer
            with fiona.open(gpkg_path, layer=layer_name) as src:
                src_crs = src.crs
                schema = src.schema

                # Create GeoJSON file
                with fiona.open(
                    geojson_path,
                    mode="w",
                    driver="GeoJSON",
                    crs=src_crs,
                    schema=schema
                ) as dst:
                    for feature in src:
                        dst.write(feature)

        except Exception as e:
            raise ValueError(f"Failed to convert GeoPackage to GeoJSON: {e}")

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
        raster_path = self.__is_raster(layer_name)
        if raster_path:
            return raster_path
       
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
        

        if self.__is_raster(new_name):
            exists = True

        return exists
        
    def get_layer_information(self, layer_id):
        """
        Retrieves metadata for a specific layer stored either as a raster file 
        or a vector layer within the default GeoPackage.

        Parameters:
            layer_id (str): The unique name/identifier of the layer.

        Returns:
            dict: A dictionary containing metadata about the layer.
                - For Raster: {'type', 'bands', 'width', 'height', 'crs', 'resolution'}
                - For Vector: {'type', 'geometry_type', 'crs', 'attributes', 'feature_count'}

        Raises:
            ValueError: If the layer is not found in either location or if the GeoPackage is unreadable.
        """

        layers_dir = os.path.join(file_manager.layers_dir)
        gpkg_path = os.path.join(layers_dir, layer_id + ".gpkg")

        raster_path = self.__is_raster(layer_id)
        if raster_path:
            with rasterio.open(raster_path) as src:
                return {
                    "type": "raster",
                    "bands": src.count,
                    "width": src.width,
                    "height": src.height,
                    "crs": src.crs.to_string() if src.crs else None,
                    "resolution": src.res
                }

        # Check if the layer_id matches a vector layer in the GeoPackage
        if os.path.isfile(gpkg_path):
            try:
                layers = fiona.listlayers(gpkg_path)
                candidate = layers[0]
                gdf = gpd.read_file(gpkg_path, layer=candidate)
                return {
                        "type": "vector",
                        "geometry_type": gdf.geom_type.mode()[0] if not gdf.empty else None,
                        "crs": gdf.crs.to_string() if gdf.crs else None,
                        "attributes": list(gdf.columns.drop("geometry")),
                        "feature_count": len(gdf)
                    }
            except Exception as e:
                raise ValueError(f"Error reading GeoPackage: {e}")

        # If neither raster nor vector layer found, raise error
        raise ValueError(f"Layer '{layer_id}' not found in rasters or GeoPackage")
    
    def get_layer_for_script(self, layer_id):
        raster_path = self.__is_raster(layer_id)

        if raster_path:
            return raster_path
        # Check if the layer_id matches a vector layer in the GeoPackage
        if os.path.isfile(self.default_gpkg_path):
            try:
                layers = fiona.listlayers(self.default_gpkg_path)
                if layer_id in layers:
                    output_gpkg = os.path.join(file_manager.temp_dir, f"{layer_id}.gpkg")

                    # Copy only the requested layer
                    with fiona.open(self.default_gpkg_path, layer=layer_id) as src:
                        meta = src.meta

                        # Write single-layer GPKG
                        with fiona.open(
                            output_gpkg,
                            mode="w",
                            **meta
                        ) as dst:
                            for feature in src:
                                dst.write(feature)

                    return output_gpkg
                            
                else:
                    return None                

            except Exception as e:
                raise ValueError(f"Error reading GeoPackage: {e}")        

    def get_layer_extension(self, layer_id):
            """
            Return the file extension for a given layer ID stored in layers_dir.

            Parameters:
                layer_id(str): The unique layer identifier.

            Returns:
                extension(str): The file extension (including the leading dot), e.g. ".gpkg", ".tif".

            """
            prefix = f"{layer_id}."
            metadata_suffix = f"{layer_id}_metadata.json"

            matches = []

            for filename in os.listdir(file_manager.layers_dir):
                if filename == metadata_suffix:
                    continue

                if filename.startswith(prefix):
                    matches.append(filename)

            if not matches:
                raise NotFound(f"No layer file found for layer_id '{layer_id}'")

            if len(matches) > 1:
                raise ValueError(
                    f"Multiple layer files found for layer_id '{layer_id}': {matches}"
                )

            _, extension = os.path.splitext(matches[0])
            return extension
    
    def tile_bounds(self, x, y, z):
        """
        Calculate the geographic bounding box of an XYZ tile in EPSG:4326.

        Parameters:
            x (int): Tile column number.
            y (int): Tile row number.
            z (int): Zoom level.

        Returns:
            (min_lon, min_lat, max_lon, max_lat): (float, float, float, float)
            The longitude and latitude bounds of the tile in degrees.
        """
        n = 2.0 ** z
        lon_deg_min = x / n * 360.0 - 180.0
        lon_deg_max = (x + 1) / n * 360.0 - 180.0
        lat_rad_min = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
        lat_rad_max = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg_min = math.degrees(lat_rad_min)
        lat_deg_max = math.degrees(lat_rad_max)
        return lon_deg_min, lat_deg_min, lon_deg_max, lat_deg_max

    def clean_raster_cache(self, cache_dir, CACHE_MAX_BYTES=500*1024*1024):
        """
        Remove oldest cached raster tiles to keep the total cache size under a limit.

        Parameters:
            cache_dir(str): Path to the cache directory containing raster tiles.
            CACHE_MAX_BYTES(int, optional): Maximum allowed size of the cache in bytes. Defaults to 500 Mb.

        Returns:
        None
        """
        files = [(os.path.join(dp, f), os.path.getatime(os.path.join(dp, f)), os.path.getsize(os.path.join(dp, f)))
                for dp, dn, filenames in os.walk(cache_dir) for f in filenames]
        
        files.sort(key=lambda x: x[1])  # oldest first
        total_size = sum(f[2] for f in files)
        
        while total_size > CACHE_MAX_BYTES and files:
            file_path, _, size = files.pop(0)
            os.remove(file_path)
            total_size -= size

    def get_metadata(self, layer_id):
        
        metadata_filename = f"{layer_id}_metadata.json"
        metadata_path = os.path.join(file_manager.layers_dir, metadata_filename)

        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
            
        return None

    #=====================================================================================
    #                               HELPER METHODS
    #=====================================================================================    

    @staticmethod
    def __check_raster_system_coordinates(raster_path, target_crs="EPSG:4326"):
        try:
            # Read the GeoTIFF file
            with rioxarray.open_rasterio(raster_path) as raster:
                if raster.rio.crs is None:
                    raise ValueError("Raster has no CRS information.")
                else:
                    return raster.rio.crs.to_string()
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
    
    @staticmethod
    def __get_gpkg_metadata(gpkg_path, crs_original):
        try:
            layers = fiona.listlayers(gpkg_path)

            gdf = gpd.read_file(gpkg_path, layer=layers[0])
            return {
                "layer_name": layers[0],    
                "type": "vector",
                "geometry_type": gdf.geom_type.mode()[0] if not gdf.empty else None,
                "crs": gdf.crs.to_string() if gdf.crs else None,
                "crs_original": crs_original,
                "attributes": list(gdf.columns.drop("geometry")),
                "feature_count": len(gdf),
                "bounding_box": gdf.total_bounds.tolist()
            }
        except Exception as e:
            raise ValueError(f"Error reading GeoPackage: {e}")

    @staticmethod
    def __get_raster_metadata(raster_path, crs_original, tile_size=256):

        with rasterio.open(raster_path) as src:
            transform = src.transform
            pixel_size_x = transform.a
            pixel_size_y = -transform.e
            pixel_size = max(pixel_size_x, pixel_size_y)

            # Max zoom = finest resolution
            zoom_max = math.ceil(math.log2(360 / (tile_size * pixel_size)))

            # Min zoom = coarse resolution (whole raster fits in one tile)
            raster_width_deg = pixel_size_x * src.width
            raster_height_deg = pixel_size_y * src.height
            raster_extent_deg = max(raster_width_deg, raster_height_deg)
            zoom_min = max(0, math.floor(math.log2(360 / (tile_size * raster_extent_deg))))

            # Bounding box (EPSG:4326)
            bounds = src.bounds
            min_lon, min_lat, max_lon, max_lat = transform_bounds(
                src.crs,
                "EPSG:4326",
                bounds.left,
                bounds.bottom,
                bounds.right,
                bounds.top,
                densify_pts=21
            )

            return {
                "type": "raster",
                "crs": src.crs.to_string() if src.crs else None,
                "crs_original": crs_original,
                "bands": src.count,
                "width": src.width,
                "height": src.height,
                "resolution": src.res,
                "zoom_min": zoom_min,
                "zoom_max": zoom_max,
                "bbox": {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat
                }    
            }

    @staticmethod
    def __move_to_permanent(temp_layer_path, layer_id, metadata_dict):
        # Move layer file to permanent storage
        _, ext = os.path.splitext(temp_layer_path)
        dest_path = os.path.join(file_manager.layers_dir, f"{layer_id}{ext}")

        try:
            if not os.path.isfile(temp_layer_path):
                 raise ValueError(f"Source file not found: {temp_layer_path}")

            shutil.move(temp_layer_path, dest_path)
        except Exception as e:
            raise ValueError(f"Failed to move layer to permanent storage: {e}")

        # Save layer metadata
        meta_path = os.path.join(file_manager.layers_dir, f"{layer_id}_metadata.json")

        try:
            with open(meta_path, 'w') as f:
                json.dump(metadata_dict, f, indent=4)
        except Exception as e:
            raise ValueError(f"Failed to save layer metadata: {e}")

        return
    
    @staticmethod
    def __is_raster(layer_id):
        """
        Docstring for __is_raster
        
        :param layer_id: Description

        Returns raster_path or None
        """
        possible_exts = [".tif", ".tiff"]
        possible_exts += [ext.upper() for ext in possible_exts]

        raster_path = None
        for ext in possible_exts:
            candidate = os.path.join(file_manager.layers_dir, layer_id + ext)
            if os.path.isfile(candidate):
                raster_path = candidate
                break
        
        return raster_path