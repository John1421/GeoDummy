import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

# Path configuration para conseguir importar DataManager
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from App.DataManager import DataManager
except ImportError:
    from DataManager import DataManager


# ============================================================================
# FIXTURE
# ============================================================================

@pytest.fixture
def dm():
    """Instância fresca de DataManager para cada teste."""
    return DataManager()


# ============================================================================
# TESTES: format_value_for_table_view()
# ============================================================================

class TestFormatValueForTableView:
    def test_none_returns_string_none(self, dm):
        # O método faz str(return_string) no fim → "None"
        assert dm.format_value_for_table_view(None) == "None"

    def test_boolean_formatted_as_int(self, dm):
        # Em Python, bool é subclass de int, por isso passa no ramo do inteiro
        assert dm.format_value_for_table_view(True) == "1"
        assert dm.format_value_for_table_view(False) == "0"

    def test_integer_thousand_separator(self, dm):
        assert dm.format_value_for_table_view(1234) == "1,234"
        assert dm.format_value_for_table_view(1234567) == "1,234,567"

    def test_float_two_decimals_and_separator(self, dm):
        out = dm.format_value_for_table_view(1234.567)
        assert out == "1,234.57"

    def test_datetime_isoformat(self, dm):
        dt = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
        assert dm.format_value_for_table_view(dt) == dt.isoformat()

    def test_string_short_unchanged(self, dm):
        s = "short string"
        assert dm.format_value_for_table_view(s) == s

    def test_string_exactly_100_not_truncated(self, dm):
        s = "a" * 100
        out = dm.format_value_for_table_view(s)
        assert out == s
        assert not out.endswith("...")

    def test_string_long_truncated(self, dm):
        long_str = "a" * 150
        out = dm.format_value_for_table_view(long_str)
        assert len(out) == 103  # 100 chars + "..."
        assert out.endswith("...")
        assert out.startswith("a" * 100)

    def test_unknown_type_fallback_str(self, dm):
        class Dummy:
            def __str__(self):
                return "dummy"
        assert dm.format_value_for_table_view(Dummy()) == "dummy"


# ============================================================================
# TESTES: detect_type()
# ============================================================================

class TestDetectType:
    def test_detect_null(self, dm):
        assert dm.detect_type(None) == "null"

    def test_detect_boolean(self, dm):
        assert dm.detect_type(True) == "boolean"
        assert dm.detect_type(False) == "boolean"

    def test_detect_int(self, dm):
        assert dm.detect_type(0) == "int"
        assert dm.detect_type(42) == "int"

    def test_detect_float(self, dm):
        assert dm.detect_type(1.5) == "float"

    def test_detect_datetime(self, dm):
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert dm.detect_type(dt) == "datetime"

    def test_detect_string(self, dm):
        assert dm.detect_type("hello") == "string"
        assert dm.detect_type("") == "string"

    def test_detect_other_defaults_to_string(self, dm):
        assert dm.detect_type([1, 2, 3]) == "string"
        assert dm.detect_type({"a": 1}) == "string"


# ============================================================================
# TESTES: Cache (insert_to_cache / check_cache)
# ============================================================================

class TestCache:
    def test_insert_and_check_cache_hit(self, dm):
        dm.insert_to_cache("test_key", "test_data", ttl_minutes=10)
        assert dm.check_cache("test_key") == "test_data"

    def test_cache_miss_unknown_key(self, dm):
        assert dm.check_cache("missing_key") is None

    def test_expired_entry_returns_none_and_is_deleted(self, dm):
        dm.insert_to_cache("expired_key", "old_data", ttl_minutes=-1)
        assert dm.check_cache("expired_key") is None
        assert "expired_key" not in dm.cache

    def test_overwrite_same_key_updates_value_and_expiry(self, dm):
        dm.insert_to_cache("k", "old", ttl_minutes=10)
        first_expiry = dm.cache["k"]["expires"]
        dm.insert_to_cache("k", "new", ttl_minutes=20)

        assert dm.check_cache("k") == "new"
        assert dm.cache["k"]["expires"] > first_expiry

    def test_expiry_timestamp_reasonable(self, dm):
        key = "ttl_key"
        ttl = 5
        before = datetime.now(timezone.utc)

        dm.insert_to_cache(key, {"ok": True}, ttl_minutes=ttl)

        after = datetime.now(timezone.utc)
        expires = dm.cache[key]["expires"]

        assert before + timedelta(minutes=ttl) <= expires <= after + timedelta(minutes=ttl)
