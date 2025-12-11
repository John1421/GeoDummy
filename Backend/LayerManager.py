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
import rasterio

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
            if gdf.crs.to_string() != target_crs:
                gdf = gdf.to_crs(target_crs)

            # 7. Determine layer name
            if layer_name is None:
                layer_name = os.path.splitext(shp_files[0])[0]

            # 8. Check for existing layer
            if self.check_layer_name_exists(layer_name):
                shutil.rmtree(temp_dir)
                raise ValueError(f"A layer with the name '{layer_name}' already exists.")

            # 9. Write to default GeoPackage
            gdf.to_file(
                self.default_gpkg_path,
                layer=layer_name,
                driver="GPKG"
            )

            # 10. Cleanup extracted files
            shutil.rmtree(temp_dir)
        except Exception as e:
            raise ValueError(f"Error writing shapefile into GeoPackage: {e}")    

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
        
        # Check if layer already exists (optional)
        if self.check_layer_name_exists(layer_name):
            raise ValueError(f"A raster layer with the name '{layer_name}' already exists.")

        try:
            # Read source layer
            gdf = gpd.read_file(geojson_path)  # can specify layer= if from a GeoPackage

            # Check CRS
            if gdf.crs is None:
                raise ValueError("Source layer has no CRS")

            # Reproject if needed
            if gdf.crs.to_string() != target_crs:
                gdf = gdf.to_crs(target_crs)

            # Write to default GeoPackage
            gdf.to_file(
                self.default_gpkg_path,
                layer=layer_name,
                driver="GPKG"
                )
        except Exception as e:
            raise ValueError(f"Error writing GeoJSON into GeoPackage: {e}")

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

    def get_layer_for_script(self, layer_id):
        possible_exts = [".tif", ".tiff"]
        raster_path = None
        for ext in possible_exts:
            candidate = os.path.join(file_manager.layers_dir, layer_id + ext)
            candidate_upper = os.path.join(file_manager.layers_dir, layer_id + ext.upper())
            if os.path.isfile(candidate):
                raster_path = candidate
                break
            elif os.path.isfile(candidate_upper):
                raster_path = candidate_upper
                break

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
    
    def get_layer_information(self, layer_id):
        """
        Retrieves basic information about a layer stored either in the default GeoPackage
        or a raster file in the input_layers folder.
        """

        layers_dir = os.path.join(file_manager.layers_dir)
        gpkg_path = os.path.join(layers_dir, "layers.gpkg")

        # Checks if the layer_id matches a raster file
        possible_exts = [".tif", ".tiff"]
        raster_path = None
        for ext in possible_exts:
            candidate = os.path.join(layers_dir, layer_id + ext)
            candidate_upper = os.path.join(layers_dir, layer_id + ext.upper())
            if os.path.isfile(candidate):
                raster_path = candidate
                break
            elif os.path.isfile(candidate_upper):
                raster_path = candidate_upper
                break

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
                if layer_id in layers:
                    gdf = gpd.read_file(gpkg_path, layer=layer_id)
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