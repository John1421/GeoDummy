
import json
from flask import Flask, request, after_this_request, jsonify, send_file
from werkzeug.exceptions import HTTPException, BadRequest
import geopandas as gpd
import shutil
import os
import ast
import zipfile
# import FileManager
from .BasemapManager import BasemapManager
from .LayerManager import LayerManager
from .ScriptManager import ScriptManager
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from functools import lru_cache


class DataManager:
    
    def __init__(self):
        self.cache = {}

    
    def format_value_for_table_view(self, value):
        '''
        Formats data as per use case UC-B-022, used in the endpoint:
        '/layers/<layer_id>/table', methods=['GET']
        
        Parameters:
            value: Value to format
        Returns:
            The value in its formated form
        '''
        # Null-safe
        if value is None:
            return None

        # Boolean → "Yes"/"No"
        if isinstance(value, bool):
            return "Yes" if value else "No"

        # Integer formatting → thousand separators
        if isinstance(value, int):
            return f"{value:,}"

        # Float formatting → 2 decimals + thousand separator
        if isinstance(value, float):
            return f"{value:,.2f}"

        # Datetime → ISO8601
        if isinstance(value, datetime):
            return value.isoformat()

        # Strings → truncate above 100 chars
        if isinstance(value, str):
            if len(value) > 100:
                return value[:100] + "..."
            return value

        # Fallback safe string
        return str(value)
    
    
    def detect_type(self, value):
        '''
        Infers data type of the value passed as argument.
        
        Parameters:
            value: Value to infer the type of
        Returns:
            (inferred format) (str): String specifying the inferred data format
        '''
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, datetime):
            return "datetime"
        if isinstance(value, str):
            return "string"
        return "string"
    
    
    def check_cache(self, cache_key):
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now(timezone.utc) < cached["expires"]:
                return cached["data"]
            del self.cache[cache_key]
            return None
        else:
            return None
        
        
    def insert_to_cache(self, cache_key, data, ttl_minutes):
        # Caching the data
        self.cache[cache_key] = {
            "data": data,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        }