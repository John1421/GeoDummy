import os
import json

class BasemapManager:
    def __init__(self, config_path='basemaps.json'):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Basemap configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            self._basemap_lookup = {b['id']: b for b in self.config.get('basemaps', [])}

    def list_basemaps(self):
        return self.config.get('basemaps', [])
    
    def get_basemap(self, basemap_id):
        return self._basemap_lookup.get(basemap_id)