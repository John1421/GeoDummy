import pytest
from datetime import datetime, timedelta, timezone
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Configuração do path para importação
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from App.DataManager import DataManager
except ImportError:
    # Fallback para importação direta
    from DataManager import DataManager


# ============================================================================
# FIXTURES - Estado e dados reutilizáveis
# ============================================================================

@pytest.fixture
def clear_cache():
    """Limpa o cache antes e depois de cada teste."""
    # Importar a variável cache global
    from App.DataManager import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cache_fixture(clear_cache):
    """Fixture que retorna a variável cache global."""
    from App.DataManager import cache
    return cache


# ============================================================================
# TESTES: format_value_for_table_view()
# ============================================================================

class TestFormatValueForTableView:
    """
    Testes para o método format_value_for_table_view() (UC-B-022)
    
    Responsável por formatar valores para exibição em tabelas.
    Casos de uso:
    - None → None
    - Boolean → "Yes"/"No"
    - Integer → "1,234"
    - Float → "1,234.56"
    - Datetime → ISO8601
    - String → truncar se > 100 chars
    """

    # ────────────────────────────────────────────────────────────────────
    # BRANCH 1: Null-safe (value is None)
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_none_returns_none(self):
        """Branch 1: value is None → return None"""
        result = DataManager.format_value_for_table_view(None)
        assert result is None
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 2: Boolean values
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_boolean_true_returns_yes(self):
        """Branch 2a: isinstance(value, bool) and value is True → 'Yes'"""
        result = DataManager.format_value_for_table_view(True)
        assert result == "Yes"
    
    def test_format_boolean_false_returns_no(self):
        """Branch 2b: isinstance(value, bool) and value is False → 'No'"""
        result = DataManager.format_value_for_table_view(False)
        assert result == "No"
    
    def test_format_boolean_order_is_important(self):
        """Verifica que boolean é testado ANTES de int (Python bool é subclass int)."""
        # Em Python: isinstance(True, int) == True
        # Portanto, a ordem de testes é CRÍTICA
        assert isinstance(True, int)  # Confirma que bool é subclass de int
        
        result = DataManager.format_value_for_table_view(True)
        assert result == "Yes"  # Deve ser "Yes", não "1"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 3: Integer values
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_integer_small(self):
        """Branch 3a: int < 1,000 → sem separador"""
        result = DataManager.format_value_for_table_view(42)
        assert result == "42"
    
    def test_format_integer_thousands(self):
        """Branch 3b: int com separador de milhares"""
        result = DataManager.format_value_for_table_view(1234)
        assert result == "1,234"
    
    def test_format_integer_large(self):
        """Branch 3c: int grande com múltiplos separadores"""
        result = DataManager.format_value_for_table_view(1234567890)
        assert result == "1,234,567,890"
    
    def test_format_integer_negative(self):
        """Branch 3d: int negativo com separador"""
        result = DataManager.format_value_for_table_view(-5000)
        assert result == "-5,000"
    
    def test_format_integer_zero(self):
        """Branch 3e: int zero"""
        result = DataManager.format_value_for_table_view(0)
        assert result == "0"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 4: Float values
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_float_simple(self):
        """Branch 4a: float pequeno com 2 decimais"""
        result = DataManager.format_value_for_table_view(3.14159)
        assert result == "3.14"
    
    def test_format_float_thousands(self):
        """Branch 4b: float grande com separador de milhares"""
        result = DataManager.format_value_for_table_view(1234.56)
        assert result == "1,234.56"
    
    def test_format_float_large(self):
        """Branch 4c: float muito grande"""
        result = DataManager.format_value_for_table_view(123456789.99)
        assert result == "123,456,789.99"
    
    def test_format_float_negative(self):
        """Branch 4d: float negativo"""
        result = DataManager.format_value_for_table_view(-1234.56)
        assert result == "-1,234.56"
    
    def test_format_float_zero(self):
        """Branch 4e: float zero"""
        result = DataManager.format_value_for_table_view(0.0)
        assert result == "0.00"
    
    def test_format_float_one_decimal(self):
        """Branch 4f: float com apenas 1 decimal"""
        result = DataManager.format_value_for_table_view(42.5)
        assert result == "42.50"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 5: Datetime values
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_datetime_iso8601(self):
        """Branch 5a: datetime → ISO8601 format"""
        dt = datetime(2026, 1, 15, 14, 30, 45)
        result = DataManager.format_value_for_table_view(dt)
        assert result == dt.isoformat()
        assert result == "2026-01-15T14:30:45"
    
    def test_format_datetime_with_timezone(self):
        """Branch 5b: datetime com timezone"""
        dt = datetime(2026, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = DataManager.format_value_for_table_view(dt)
        assert result == dt.isoformat()
    
    def test_format_datetime_with_microseconds(self):
        """Branch 5c: datetime com microsegundos"""
        dt = datetime(2026, 1, 15, 14, 30, 45, 123456)
        result = DataManager.format_value_for_table_view(dt)
        assert "2026-01-15T14:30:45" in result
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 6: String values
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_string_short(self):
        """Branch 6a: string < 100 chars → sem truncamento"""
        text = "Hello, World!"
        result = DataManager.format_value_for_table_view(text)
        assert result == text
    
    def test_format_string_exactly_100_chars(self):
        """Branch 6b: string = 100 chars → sem truncamento"""
        text = "x" * 100
        result = DataManager.format_value_for_table_view(text)
        assert result == text
        assert len(result) == 100
    
    def test_format_string_101_chars(self):
        """Branch 6c: string = 101 chars → truncamento + '...'"""
        text = "x" * 101
        result = DataManager.format_value_for_table_view(text)
        assert result == "x" * 100 + "..."
        assert len(result) == 103  # 100 + 3 pontos
    
    def test_format_string_very_long(self):
        """Branch 6d: string muito longa → truncada a 100 chars + '...'"""
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5  # ~290 chars
        result = DataManager.format_value_for_table_view(text)
        assert result.endswith("...")
        assert len(result) == 103
        assert result[:100] == text[:100]
    
    def test_format_string_empty(self):
        """Branch 6e: string vazia → retorna vazia"""
        result = DataManager.format_value_for_table_view("")
        assert result == ""
    
    def test_format_string_with_special_chars(self):
        """Branch 6f: string com caracteres especiais"""
        text = "José da Silva - Rua da Luz, 123"
        result = DataManager.format_value_for_table_view(text)
        assert result == text
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 7: Fallback (custom objects)
    # ────────────────────────────────────────────────────────────────────
    
    def test_format_custom_object_fallback(self):
        """Branch 7: objeto custom → str(value)"""
        class CustomObj:
            def __str__(self):
                return "CustomObject"
        
        obj = CustomObj()
        result = DataManager.format_value_for_table_view(obj)
        assert result == "CustomObject"
    
    def test_format_list_fallback(self):
        """Branch 7: lista → str(value)"""
        lst = [1, 2, 3]
        result = DataManager.format_value_for_table_view(lst)
        assert result == str(lst)
    
    def test_format_dict_fallback(self):
        """Branch 7: dicionário → str(value)"""
        d = {"key": "value"}
        result = DataManager.format_value_for_table_view(d)
        assert result == str(d)


# ============================================================================
# TESTES: detect_type()
# ============================================================================

class TestDetectType:
    """
    Testes para o método detect_type()
    
    Infere o tipo de dado de um valor.
    Retorna: "null", "boolean", "int", "float", "datetime", "string"
    """

    # ────────────────────────────────────────────────────────────────────
    # BRANCH 1: Null detection
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_none(self):
        """Branch 1: value is None → 'null'"""
        assert DataManager.detect_type(None) == "null"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 2: Boolean detection (ANTES de int)
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_boolean_true(self):
        """Branch 2a: isinstance(value, bool) True → 'boolean'"""
        assert DataManager.detect_type(True) == "boolean"
    
    def test_detect_type_boolean_false(self):
        """Branch 2b: isinstance(value, bool) False → 'boolean'"""
        assert DataManager.detect_type(False) == "boolean"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 3: Integer detection
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_integer_positive(self):
        """Branch 3a: isinstance(value, int) com int positivo → 'int'"""
        assert DataManager.detect_type(42) == "int"
    
    def test_detect_type_integer_negative(self):
        """Branch 3b: isinstance(value, int) com int negativo → 'int'"""
        assert DataManager.detect_type(-42) == "int"
    
    def test_detect_type_integer_zero(self):
        """Branch 3c: isinstance(value, int) com zero → 'int'"""
        assert DataManager.detect_type(0) == "int"
    
    def test_detect_type_integer_large(self):
        """Branch 3d: isinstance(value, int) com número grande → 'int'"""
        assert DataManager.detect_type(999999999999) == "int"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 4: Float detection
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_float_positive(self):
        """Branch 4a: isinstance(value, float) com float positivo → 'float'"""
        assert DataManager.detect_type(3.14) == "float"
    
    def test_detect_type_float_negative(self):
        """Branch 4b: isinstance(value, float) com float negativo → 'float'"""
        assert DataManager.detect_type(-3.14) == "float"
    
    def test_detect_type_float_zero(self):
        """Branch 4c: isinstance(value, float) com zero → 'float'"""
        assert DataManager.detect_type(0.0) == "float"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 5: Datetime detection
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_datetime(self):
        """Branch 5a: isinstance(value, datetime) → 'datetime'"""
        dt = datetime(2026, 1, 15, 14, 30, 45)
        assert DataManager.detect_type(dt) == "datetime"
    
    def test_detect_type_datetime_with_timezone(self):
        """Branch 5b: datetime com timezone → 'datetime'"""
        dt = datetime(2026, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        assert DataManager.detect_type(dt) == "datetime"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 6: String detection
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_string(self):
        """Branch 6a: isinstance(value, str) → 'string'"""
        assert DataManager.detect_type("hello") == "string"
    
    def test_detect_type_string_empty(self):
        """Branch 6b: string vazia → 'string'"""
        assert DataManager.detect_type("") == "string"
    
    def test_detect_type_string_with_special_chars(self):
        """Branch 6c: string com caracteres especiais → 'string'"""
        assert DataManager.detect_type("José da Silva") == "string"
    
    # ────────────────────────────────────────────────────────────────────
    # BRANCH 7: Fallback
    # ────────────────────────────────────────────────────────────────────
    
    def test_detect_type_list_fallback(self):
        """Branch 7a: lista não é nenhum tipo específico → 'string'"""
        assert DataManager.detect_type([1, 2, 3]) == "string"
    
    def test_detect_type_dict_fallback(self):
        """Branch 7b: dicionário → 'string' (fallback)"""
        assert DataManager.detect_type({"key": "value"}) == "string"
    
    def test_detect_type_custom_object_fallback(self):
        """Branch 7c: objeto custom → 'string' (fallback)"""
        class CustomObj:
            pass
        assert DataManager.detect_type(CustomObj()) == "string"


# ============================================================================
# TESTES: check_cache()
# ============================================================================

class TestCheckCache:
    """
    Testes para o método check_cache()
    
    Verifica se uma chave existe no cache e se ainda é válida (não expirou).
    Retorna: dados do cache ou None
    """

    def test_check_cache_key_not_exists(self, clear_cache):
        """Branch 1: cache_key not in cache → return None"""
        result = DataManager.check_cache("nonexistent_key")
        assert result is None
    
    def test_check_cache_key_exists_not_expired(self, clear_cache, cache_fixture):
        """Branch 2a: cache_key in cache AND not expired → return data"""
        # Preparar dados na cache
        cache_fixture["test_key"] = {
            "data": {"id": 1, "name": "Alice"},
            "expires": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        
        # Verificar a cache
        result = DataManager.check_cache("test_key")
        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Alice"
    
    def test_check_cache_key_exists_expired(self, clear_cache, cache_fixture):
        """Branch 2b: cache_key in cache BUT expired → delete & return None"""
        # Preparar dados EXPIRADOS na cache
        cache_fixture["expired_key"] = {
            "data": {"id": 2, "name": "Bob"},
            "expires": datetime.now(timezone.utc) - timedelta(minutes=5)  # Expirou há 5 minutos
        }
        
        # Verificar a cache
        result = DataManager.check_cache("expired_key")
        
        # Deve retornar None
        assert result is None
        
        # Deve ter removido da cache
        assert "expired_key" not in cache_fixture
    
    def test_check_cache_expiry_boundary(self, clear_cache, cache_fixture):
        """Branch 2c: exatamente no momento de expiração"""
        now = datetime.now(timezone.utc)
        
        cache_fixture["boundary_key"] = {
            "data": {"value": 42},
            "expires": now  # Expira AGORA
        }
        
        # Condição: datetime.now() < cached["expires"] é Falso pq expirou
        result = DataManager.check_cache("boundary_key")
        assert result is None
    
    def test_check_cache_just_before_expiry(self, clear_cache, cache_fixture):
        """Branch 2d: um segundo antes de expirar"""
        cache_fixture["valid_key"] = {
            "data": {"value": 42},
            "expires": datetime.now(timezone.utc) + timedelta(seconds=1)
        }
        
        result = DataManager.check_cache("valid_key")
        assert result is not None
        assert result["value"] == 42
    
    def test_check_cache_multiple_keys(self, clear_cache, cache_fixture):
        """Branch 2e:  chaves múltiplas, uma válida, uma expirada"""
        now = datetime.now(timezone.utc)
        
        cache_fixture["valid"] = {
            "data": "data1",
            "expires": now + timedelta(minutes=10)
        }
        cache_fixture["expired"] = {
            "data": "data2",
            "expires": now - timedelta(minutes=10)
        }
        
        assert DataManager.check_cache("valid") == "data1"
        assert DataManager.check_cache("expired") is None
        assert "expired" not in cache_fixture
        assert "valid" in cache_fixture
    
    def test_check_cache_return_type_complex_data(self, clear_cache, cache_fixture):
        """Verifica retorno dos dados complexos"""
        complex_data = {
            "id": 1,
            "items": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        cache_fixture["complex_key"] = {
            "data": complex_data,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        
        result = DataManager.check_cache("complex_key")
        assert result == complex_data
        assert result["items"] == [1, 2, 3]
        assert result["nested"]["key"] == "value"


# ============================================================================
# TESTES: insert_to_cache()
# ============================================================================

class TestInsertToCache:
    """
    Testes para o método insert_to_cache()
    
    Insere dados no cache com TTL (time-to-live) em minutos.
    """

    def test_insert_to_cache_basic(self, clear_cache, cache_fixture):
        """Insert cache com TTL padrão"""
        data = {"id": 1, "name": "Alice"}
        DataManager.insert_to_cache("key1", data, 10)
        
        assert "key1" in cache_fixture
        assert cache_fixture["key1"]["data"] == data
        assert cache_fixture["key1"]["expires"] is not None
    
    def test_insert_to_cache_ttl_10_minutes(self, clear_cache, cache_fixture):
        """TTL 10 minutos → expira em +/-10 minutos"""
        before = datetime.now(timezone.utc)
        DataManager.insert_to_cache("key_10m", {"value": 42}, 10)
        after = datetime.now(timezone.utc)
        
        expires = cache_fixture["key_10m"]["expires"]
        
        # Deve expirar entre 10 e 10 minutos + alguns segundos
        min_time = before + timedelta(minutes=10)
        max_time = after + timedelta(minutes=10) + timedelta(seconds=5)
        
        assert min_time <= expires <= max_time
    
    def test_insert_to_cache_ttl_1_minute(self, clear_cache, cache_fixture):
        """TTL 1 minuto"""
        before = datetime.now(timezone.utc)
        DataManager.insert_to_cache("key_1m", "data", 1)
        after = datetime.now(timezone.utc)
        
        expires = cache_fixture["key_1m"]["expires"]
        min_time = before + timedelta(minutes=1)
        max_time = after + timedelta(minutes=1) + timedelta(seconds=5)
        
        assert min_time <= expires <= max_time
    
    def test_insert_to_cache_ttl_60_minutes(self, clear_cache, cache_fixture):
        """TTL 60 minutos (1 hora)"""
        before = datetime.now(timezone.utc)
        DataManager.insert_to_cache("key_1h", {"data": "test"}, 60)
        after = datetime.now(timezone.utc)
        
        expires = cache_fixture["key_1h"]["expires"]
        min_time = before + timedelta(minutes=60)
        max_time = after + timedelta(minutes=60) + timedelta(seconds=5)
        
        assert min_time <= expires <= max_time
    
    def test_insert_to_cache_overwrite_existing(self, clear_cache, cache_fixture):
        """Sobrescreve a chave existente"""
        DataManager.insert_to_cache("key", "data1", 10)
        assert cache_fixture["key"]["data"] == "data1"
        
        DataManager.insert_to_cache("key", "data2", 20)
        assert cache_fixture["key"]["data"] == "data2"
    
    def test_insert_to_cache_complex_data(self, clear_cache, cache_fixture):
        """Insert dos dados complexos (dict, list)"""
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "metadata": {"version": 1}
        }
        
        DataManager.insert_to_cache("complex", complex_data, 30)
        
        retrieved = cache_fixture["complex"]["data"]
        assert retrieved["users"][0]["name"] == "Alice"
        assert retrieved["metadata"]["version"] == 1
    
    def test_insert_to_cache_with_timezone(self, clear_cache, cache_fixture):
        """Verifica que usa timezone UTC"""
        DataManager.insert_to_cache("tz_key", "data", 5)
        
        expires = cache_fixture["tz_key"]["expires"]
        assert expires.tzinfo == timezone.utc
    
    def test_insert_to_cache_zero_ttl(self, clear_cache, cache_fixture):
        """TTL 0 minutos → expira AGORA"""
        DataManager.insert_to_cache("zero_ttl", "data", 0)
        
        # Deve estar no cache
        assert "zero_ttl" in cache_fixture
        
        # Mas deve estar expirado (ou muito perto)
        expires = cache_fixture["zero_ttl"]["expires"]
        assert expires <= datetime.now(timezone.utc) + timedelta(seconds=1)
    
    def test_insert_to_cache_multiple_keys(self, clear_cache, cache_fixture):
        """Insere múltiplas chaves com diferentes TTLs"""
        DataManager.insert_to_cache("key1", "data1", 10)
        DataManager.insert_to_cache("key2", "data2", 20)
        DataManager.insert_to_cache("key3", "data3", 30)
        
        assert len(cache_fixture) == 3
        assert cache_fixture["key1"]["data"] == "data1"
        assert cache_fixture["key2"]["data"] == "data2"
        assert cache_fixture["key3"]["data"] == "data3"


# ============================================================================
# TESTES DE INTEGRAÇÃO
# ============================================================================

class TestCacheIntegration:
    """Testes de fluxos integrados entre check_cache e insert_to_cache."""

    def test_cache_workflow_insert_then_check(self, clear_cache):
        """Workflow: insert → check"""
        # Insert
        data = {"id": 1, "status": "active"}
        DataManager.insert_to_cache("workflow_key", data, 15)
        
        # Check
        retrieved = DataManager.check_cache("workflow_key")
        assert retrieved == data
    
    def test_cache_workflow_insert_check_expired(self, clear_cache, cache_fixture):
        """Workflow: insert → wait expiry → check"""
        # Insert com TTL muito curto
        DataManager.insert_to_cache("short_ttl", {"value": 99}, 0)
        
        # Modificar manualmente a expiração para garantir que expirou
        cache_fixture["short_ttl"]["expires"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        # Check (deve estar expirado)
        result = DataManager.check_cache("short_ttl")
        assert result is None
        assert "short_ttl" not in cache_fixture
    
    def test_cache_workflow_multiple_operations(self, clear_cache, cache_fixture):
        """Múltiplas operações em sequência"""
        # Insert 3 items
        DataManager.insert_to_cache("item1", {"data": 1}, 10)
        DataManager.insert_to_cache("item2", {"data": 2}, 20)
        DataManager.insert_to_cache("item3", {"data": 3}, 5)
        
        # Expirar item3
        cache_fixture["item3"]["expires"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        # Verificar estado final
        assert DataManager.check_cache("item1") is not None
        assert DataManager.check_cache("item2") is not None
        assert DataManager.check_cache("item3") is None
        
        # item3 deve ter sido removido
        assert "item3" not in cache_fixture
        assert len(cache_fixture) == 2


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Casos extremos e situações especiais."""

    def test_format_string_exactly_at_boundary(self):
        """String com exatamente 100 caracteres (se está no limite)"""
        text = "x" * 100
        result = DataManager.format_value_for_table_view(text)
        assert result == text
        assert not result.endswith("...")
    
    def test_format_string_one_char_over_boundary(self):
        """String com 101 caracteres (ultrapassa o limite)"""
        text = "x" * 101
        result = DataManager.format_value_for_table_view(text)
        assert result.endswith("...")
        assert len(result) == 103
    
    def test_detect_type_preserves_boolean_before_int(self):
        """Checka se o bool é testado antes do int"""
        assert DataManager.detect_type(True) == "boolean"
        assert DataManager.detect_type(False) == "boolean"
        
        # Não quero que retorne um "int"
        assert DataManager.detect_type(True) != "int"
    
    def test_cache_timezone_awareness(self, clear_cache, cache_fixture):
        """Cache usa timezone-aware datetimes (UTC)"""
        DataManager.insert_to_cache("tz_test", "data", 10)
        
        expires = cache_fixture["tz_test"]["expires"]
        
        # Deve ser timezone-aware
        assert expires.tzinfo is not None
        assert expires.tzinfo == timezone.utc
    
    def test_format_float_precision(self):
        """Float sempre formatado com exatamente 2 decimais"""
        assert DataManager.format_value_for_table_view(1.0) == "1.00"
        assert DataManager.format_value_for_table_view(1.5) == "1.50"
        assert DataManager.format_value_for_table_view(1.567) == "1.57"


# ============================================================================
# CONFIGURAÇÃO DO PYTEST
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=App.DataManager",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])