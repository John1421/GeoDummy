"""
Layer management module for geospatial data.

This module provides the LayerManager class for handling vector and raster geospatial
layers. It supports importing, exporting, and managing various geospatial formats
including Shapefiles, GeoJSON, GeoPackages, and GeoTIFF rasters.

The module handles:
    - Format conversion between different geospatial formats
    - Coordinate reference system (CRS) transformations
    - Layer metadata management
    - Tile generation for web mapping
    - Cache management for raster tiles
"""

import json
import math
import os
import shutil
import uuid
import zipfile

import fiona
import geopandas as gpd
import rasterio
import rioxarray
from fiona.errors import FionaValueError
from rasterio.warp import transform_bounds
from werkzeug.exceptions import NotFound

from .FileManager import FileManager

file_manager = FileManager()

class LayerManager:
    """
    Manages geospatial layers including import, export, and metadata operations.
    
    This class handles both vector (Shapefile, GeoJSON, GeoPackage) and raster
    (GeoTIFF) geospatial data formats.
    """

    MAX_LAYER_FILE_SIZE = 1000 * 1024 * 1024 # 1000 MB
    def __init__(self):
        """
        Initialize LayerManager and perform integrity checks on existing layers.
        
        Scans the layers directory for orphaned files and removes them to maintain
        data integrity.
        """

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
        Import a zipped ESRI Shapefile and convert it into a GeoPackage layer.

        :param zip_path: Absolute path to the ZIP file containing shapefile components.
        :param layer_name: Name for the layer in the GeoPackage. If None, uses shapefile base name.
        :param target_crs: Target coordinate reference system. Defaults to "EPSG:4326".
        :return: Tuple of (new_gpkg_id, metadata) where new_gpkg_id is a UUID and metadata a dict.
        :raises ValueError: If ZIP is invalid, no .shp file found, no CRS, or processing fails.
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
        Import a GeoJSON file and convert it into a GeoPackage layer.

        :param geojson_path: Path to the .geojson file.
        :param layer_name: Name for the layer in the GeoPackage. Defaults to None.
        :param target_crs: Target coordinate reference system. Defaults to "EPSG:4326".
        :return: Tuple of (new_gpkg_id, metadata) where new_gpkg_id is a UUID and metadata a dict.
        :raises ValueError: If file doesn't exist, has no CRS, or processing fails.
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
        Import a GeoTIFF raster file into the layer storage system.

        :param raster_path: Path to the .tif or .tiff file.
        :param layer_name: Name for the raster layer. If None, derives from file basename.
        :param target_crs: Target coordinate reference system. Defaults to "EPSG:4326".
        :return: Tuple of (layer_name, metadata), metadata includes dimensions, CRS, zoom levels.
        :raises ValueError: If file doesn't exist, layer name already exists, or processing fails.
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

    def add_gpkg_layers(self, geopackage_path, target_crs="EPSG:4326", selected_layers=None):
        """
        Import selected layers from an external GeoPackage into the application's storage.

        :param geopackage_path: Path to the incoming .gpkg file.
        :param target_crs: CRS to convert vector layers to. Defaults to "EPSG:4326".
        :param selected_layers: Optional list of layer names to import. If None, imports all layers.
        :return: Tuple of (list of new_gpkg_ids, list of metadata dicts).
        :raises ValueError: If file doesn't exist, is invalid, or contains conflicting layer names.
        """

        incoming_layers = self.__retrieve_spatial_layers_from_incoming_gpkg(geopackage_path)

        # If selected_layers is provided, filter to only those layers
        if selected_layers:
            incoming_layers = [layer for layer in incoming_layers if layer in selected_layers]
            if not incoming_layers:
                raise ValueError("No valid layers found in the selected layer names.")

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
        Extract a layer from a GeoPackage and save it as a GeoJSON file.

        :param layer_id: The id of the GeoPackage.
        :return: Path to the exported GeoJSON file.
        :raises ValueError: If GeoPackage has no layers or conversion fails.
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
        Locate and return the path to a raster layer.

        :param layer_name: Name of the raster layer (without extension).
        :return: Full path to the raster file.
        :raises ValueError: If the raster does not exist.
        """
        raster_path = self.is_raster(layer_name)

        if raster_path:
            return raster_path

        raise ValueError(f"Raster layer '{layer_name}' not found in layers directory.")

    def check_layer_name_exists(self, new_name):
        """
        Check if a layer with the given name exists.

        :param new_name: Layer name to check.
        :return: True if the layer exists, False otherwise.
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


        if self.is_raster(new_name):
            exists = True

        return exists

    def get_layer_information(self, layer_id):
        """
        Retrieve metadata for a specific layer (raster or vector).

        :param layer_id: The unique name/identifier of the layer.
        :return: Dictionary containing layer metadata (type, geometry, CRS, attributes, etc.).
        :raises ValueError: If the layer is not found or GeoPackage is unreadable.
        """

        layers_dir = os.path.join(file_manager.layers_dir)
        gpkg_path = os.path.join(layers_dir, layer_id + ".gpkg")

        raster_path = self.is_raster(layer_id)
        raster_path = self.is_raster(layer_id)
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
        """
        Get the file path for a layer to be used in scripts.

        :param layer_id: The unique layer identifier.
        :return: Path to the layer file, or None if not found.
        """

        raster_path = self.is_raster(layer_id)

        if raster_path:
            return raster_path

        # Check if the layer_id matches a vector layer in the GeoPackage
        path = os.path.join(file_manager.layers_dir, f"{layer_id}.gpkg")
        if os.path.isfile(path):
            return path

        return None

    def get_layer_extension(self, layer_id):
        """
        Return the file extension for a given layer ID.
        
        :param layer_id: The unique layer identifier.
        :return: The file extension (including the leading dot), e.g. ".gpkg", ".tif".
        :raises NotFound: If no layer file found for the given layer_id.
        :raises ValueError: If multiple layer files found for the same layer_id.
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

        :param x: Tile column number.
        :param y: Tile row number.
        :param z: Zoom level.
        :return: Tuple of (min_lon, min_lat, max_lon, max_lat) in degrees.
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
        Remove oldest cached raster tiles to keep total cache size under a limit.

        :param cache_dir: Path to the cache directory containing raster tiles.
        :param cache_max_bytes: Maximum allowed size of the cache in bytes. Defaults to 500 MB.
        """

        files = [
            (
                os.path.join(root, filename),
                os.path.getatime(os.path.join(root, filename)),
                os.path.getsize(os.path.join(root, filename)),
            )
            for root, _, filenames in os.walk(cache_dir)
            for filename in filenames
        ]

        files.sort(key=lambda x: x[1])  # oldest first
        total_size = sum(f[2] for f in files)

        while total_size > CACHE_MAX_BYTES and files:
            file_path, _, size = files.pop(0)
            os.remove(file_path)
            total_size -= size

    def get_metadata(self, layer_id):
        """
        Retrieve metadata for a layer by its ID.

        :param layer_id: The unique layer identifier.
        :return: Dictionary containing layer metadata, or None if not found.
        """


        metadata_filename = f"{layer_id}_metadata.json"
        metadata_path = os.path.join(file_manager.layers_dir, metadata_filename)

        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    def get_geopackage_layers(self, gpkg_path):
        """
        Retrieve the list of spatial layers from a GeoPackage without importing them.

        :param gpkg_path: Path to the GeoPackage file.
        :return: List of layer names in the GeoPackage.
        :raises ValueError: If file is not a valid GeoPackage or contains no spatial layers.
        """

        if not os.path.isfile(gpkg_path):
            raise ValueError("GeoPackage file does not exist.")

        try:
            spatial_layers = self.__retrieve_spatial_layers_from_incoming_gpkg(gpkg_path)
            return spatial_layers
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error reading GeoPackage: {e}")

    #=====================================================================================
    #                               HELPER METHODS
    #=====================================================================================

    def list_layer_ids(self):
        """
        List all existing layer IDs with their respective metadata.

        :return: Tuple of (list of layer_ids, list of metadata dicts).
        """

        layer_ids = []
        metadata_list = []

        try:
            for filename in os.listdir(file_manager.layers_dir):
                if not filename.endswith("_metadata.json"):
                    continue

                layer_id = filename.replace("_metadata.json", "")
                metadata_path = os.path.join(file_manager.layers_dir, filename)

                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    meta = None

                layer_ids.append(layer_id)
                metadata_list.append(meta)
        except FileNotFoundError:
            return [], []

        return layer_ids, metadata_list


    @staticmethod
    def __check_raster_system_coordinates(raster_path):
        """
        Check the coordinate reference system of a raster file.

        :param raster_path: Path to the raster file.
        :return: CRS string of the raster.
        :raises ValueError: If raster has no CRS information or reading fails.
        """

        try:
            # Read the GeoTIFF file
            with rioxarray.open_rasterio(raster_path) as raster:
                if raster.rio.crs is None:
                    raise ValueError("Raster has no CRS information.")

                return raster.rio.crs.to_string()
        except Exception as e:
            raise ValueError(f"Error checking tif CRS: {e}")


    @staticmethod
    def __convert_raster_system_coordinates(raster_path,target_crs="EPSG:4326"):
        """
        Convert a raster to a target coordinate reference system.

        :param raster_path: Path to the raster file.
        :param target_crs: Target CRS. Defaults to "EPSG:4326".
        :return: Path to the converted raster file.
        :raises ValueError: If conversion fails.
        """

        temp_path = "very_complex_raster_name_temp.tiff"
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
        """
        Extract spatial layer names from a GeoPackage file.

        :param new_geopackage_path: Path to the GeoPackage file.
        :return: List of spatial layer names.
        :raises ValueError: If GeoPackage is invalid or contains no spatial layers.
        """

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
        """
        Extract metadata from a GeoPackage layer.

        :param gpkg_path: Path to the GeoPackage file.
        :param crs_original: Original CRS string before any transformation.
        :return: Dictionary containing layer metadata.
        :raises ValueError: If reading GeoPackage fails.
        """

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
        """
        Extract metadata from a raster file including zoom levels for tile serving.

        :param raster_path: Path to the raster file.
        :param crs_original: Original CRS string before any transformation.
        :param tile_size: Tile size in pixels. Defaults to 256.
        :return: Dictionary containing raster metadata.
        """

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
    def _sanitize_for_json(data):
        """Recursively replace NaN/Infinity with None so metadata is valid JSON."""
        if isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return None
            return data
        if isinstance(data, dict):
            return {k: LayerManager._sanitize_for_json(v) for k, v in data.items()}
        if isinstance(data, list):
            return [LayerManager._sanitize_for_json(v) for v in data]
        return data

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
                clean_metadata = LayerManager._sanitize_for_json(metadata_dict)
                json.dump(clean_metadata, f, indent=4, allow_nan=False)
        except Exception as e:
            raise ValueError(f"Failed to save layer metadata: {e}")

    def is_raster(self, layer_id):
        """
        Docstring for is_raster

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
