"""
Basemap manager module.

Provides functionality for loading and retrieving basemap
configurations from a JSON file.
"""

import os
import json

class BasemapManager:
    """
    Manages basemap configurations loaded from a JSON file.
    """

    def __init__(self, config_path='./App/basemaps.json'):
        """
        Initialize the BasemapManager.

        :param config_path: Path to the basemap configuration JSON file.
        :raises FileNotFoundError: If the configuration file does not exist.
        """

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Basemap configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            self._basemap_lookup = {b['id']: b for b in self.config.get('basemaps', [])}

    def list_basemaps(self):
        """
        Return the list of available basemaps.

        :return: List of basemap configurations.
        """

        return self.config.get('basemaps', [])

    def get_basemap(self, basemap_id):
        """
        Retrieve a basemap by its identifier.

        :param basemap_id: Unique identifier of the basemap.
        :return: Basemap configuration dictionary or None if not found.
        """

        return self._basemap_lookup.get(basemap_id)
    