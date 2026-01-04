import pytest
from datetime import datetime, timedelta, timezone
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Path configuration for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from App.DataManager import DataManager
except ImportError:
    from DataManager import DataManager

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def dm():
    """Provides a fresh instance of DataManager for each test."""
    return DataManager()

# ============================================================================
# TESTS: format_value_for_table_view()
# ============================================================================

class TestFormatValueForTableView:
    """
    Tests for the format_value_for_table_view() method (UC-B-022)
    """

    def test_format_none_returns_none(self, dm):
        assert dm.format_value_for_table_view(None) is None
    
    def test_format_boolean(self, dm):
        assert dm.format_value_for_table_view(True) == "Yes"
        assert dm.format_value_for_table_view(False) == "No"
    
    def test_format_integer(self, dm):
        assert dm.format_value_for_table_view(1234) == "1,234"
    
    def test_format_float(self, dm):
        assert dm.format_value_for_table_view(1234.567) == "1,234.57"
    
    def test_format_datetime(self, dm):
        dt = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
        assert dm.format_value_for_table_view(dt) == dt.isoformat()
    
    def test_format_string_truncation(self, dm):
        long_str = "a" * 150
        result = dm.format_value_for_table_view(long_str)
        assert len(result) == 103  # 100 chars + "..."

# ============================================================================
# TESTS: detect_type()
# ============================================================================

class TestDetectType:
    def test_detect_none(self, dm):
        assert dm.detect_type(None) == "null"

    def test_detect_boolean(self, dm):
        assert dm.detect_type(True) == "boolean"

    def test_detect_numeric(self, dm):
        assert dm.detect_type(1) == "int"
        assert dm.detect_type(1.5) == "float"

# ============================================================================
# TESTS: Cache Management
# ============================================================================

class TestCache:
    def test_insert_and_check_cache(self, dm):
        dm.insert_to_cache("test_key", "test_data", 10)
        assert dm.check_cache("test_key") == "test_data"

    def test_expired_cache(self, dm):
        dm.insert_to_cache("expired_key", "old_data", -1)
        assert dm.check_cache("expired_key") is None