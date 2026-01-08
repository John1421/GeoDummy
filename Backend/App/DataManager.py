"""
Data manager module.

Provides utilities for formatting values, inferring data types,
and managing a simple in-memory cache with expiration.
"""

from datetime import datetime, timedelta, timezone


class DataManager:
    """
    Handles data formatting, type inference, and caching operations.
    """

    def __init__(self):
        """
        Initialize the DataManager with an empty cache.
        """

        self.cache = {}


    def format_value_for_table_view(self, value):
        """
        Format a value for table view representation.

        Used in use case UC-B-022 and the endpoint:
        '/layers/<layer_id>/table', methods=['GET'].

        :param value: Value to format.
        :return: Formatted value.
        """
        return_string = value

        # Null-safe
        if value is None:
            return_string = None

        # Boolean → "Yes"/"No"
        if isinstance(value, bool):
            return_string = "Yes" if value else "No"

        # Integer formatting → thousand separators
        if isinstance(value, int):
            return_string = f"{value:,}"

        # Float formatting → 2 decimals + thousand separator
        if isinstance(value, float):
            return_string =  f"{value:,.2f}"

        # Datetime → ISO8601
        if isinstance(value, datetime):
            return_string =  value.isoformat()

        # Strings → truncate above 100 chars
        if isinstance(value, str):
            if len(value) > 100:
                return_string =  value[:100] + "..."
            else:
                return_string =  value

        # Fallback safe string
        return str(return_string)

    def detect_type(self, value):
        """
        Infer the data type of a value.

        :param value: Value whose type should be inferred.
        :return: String representing the inferred type.
        """
        return_value = "string"

        if value is None:
            return_value = "null"
        elif isinstance(value, bool):
            return_value = "boolean"
        elif isinstance(value, int):
            return_value = "int"
        elif isinstance(value, float):
            return_value = "float"
        elif isinstance(value, datetime):
            return_value = "datetime"
        elif isinstance(value, str):
            return_value = "string"

        return return_value

    def check_cache(self, cache_key):
        """
        Retrieve cached data if it exists and has not expired.

        :param cache_key: Key identifying the cached entry.
        :return: Cached data or None if missing or expired.
        """

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now(timezone.utc) < cached["expires"]:
                return cached["data"]
            del self.cache[cache_key]

        return None

    def insert_to_cache(self, cache_key, data, ttl_minutes):
        """
        Insert data into the cache with a time-to-live.

        :param cache_key: Key identifying the cached entry.
        :param data: Data to cache.
        :param ttl_minutes: Time-to-live in minutes.
        """

        # Caching the data
        self.cache[cache_key] = {
            "data": data,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        }
