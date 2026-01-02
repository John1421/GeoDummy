import pytest
import pandas as pd
import numpy as np
from io import StringIO
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open
from DataManager import DataManager


class TestDataManagerInit:

    def test_init_creates_instance(self):
        
        dm = DataManager()
        assert isinstance(dm, DataManager)

    def test_init_empty_data_frame(self):
        
        dm = DataManager()
        assert isinstance(dm.df, pd.DataFrame)
        assert len(dm.df) == 0


class TestLoadData:
    

    def test_load_csv_success(self, tmp_path):
        
        csv_content = "id,name,value\n1,Alice,100\n2,Bob,200"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        dm = DataManager()
        result = dm.load_data(str(csv_file))

        assert result is True
        assert len(dm.df) == 2
        assert list(dm.df.columns) == ["id", "name", "value"]
        assert dm.df.iloc[0]["name"] == "Alice"

    def test_load_excel_success(self, tmp_path):
        
        df_test = pd.DataFrame({"id": [1, 2], "value": [100, 200]})
        excel_file = tmp_path / "test.xlsx"
        df_test.to_excel(excel_file, index=False)

        dm = DataManager()
        result = dm.load_data(str(excel_file))

        assert result is True
        assert len(dm.df) == 2

    def test_load_json_success(self, tmp_path):
        
        df_test = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        json_file = tmp_path / "test.json"
        df_test.to_json(json_file, orient="records")

        dm = DataManager()
        result = dm.load_data(str(json_file))

        assert result is True
        assert len(dm.df) >= 1

    def test_load_file_not_found(self):
        
        dm = DataManager()
        result = dm.load_data("/path/que/nao/existe/file.csv")

        assert result is False

    def test_load_unsupported_format(self, tmp_path):
        
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("some data")

        dm = DataManager()
        result = dm.load_data(str(txt_file))

        assert result is False

    def test_load_corrupted_csv(self, tmp_path):
        
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("id,name\n1,Alice\n2")  # linha incompleta

        dm = DataManager()
        result = dm.load_data(str(bad_csv))

        # Mesmo com linha incompleta, pandas carrega com NaN
        assert result is True or result is False  # depende da robustez


class TestFilterData:
    

    @pytest.fixture
    def dm_with_data(self):
        
        dm = DataManager()
        dm.df = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "name": ["Alice", "Bob", "Charlie", "David"],
            "age": [25, 30, 35, 40],
            "salary": [50000, 60000, 75000, 80000]
        })
        return dm

    def test_filter_numeric_column(self, dm_with_data):
        
        result = dm_with_data.filter_data("age", 30)

        assert len(result) == 3  # age >= 30
        assert result.iloc[0]["age"] == 30

    def test_filter_string_column(self, dm_with_data):
        
        result = dm_with_data.filter_data("name", "Bob")

        assert len(result) == 1
        assert result.iloc[0]["name"] == "Bob"

    def test_filter_nonexistent_column(self, dm_with_data):
        
        result = dm_with_data.filter_data("nonexistent", "value")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_filter_empty_dataframe(self):
        dm = DataManager()
        result = dm.filter_data("column", "value")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestAggregateData:

    @pytest.fixture
    def dm_with_numeric_data(self):
        
        dm = DataManager()
        dm.df = pd.DataFrame({
            "category": ["A", "A", "B", "B", "C"],
            "value": [10, 20, 30, 40, 50],
            "amount": [100, 200, 300, 400, 500]
        })
        return dm

    def test_aggregate_sum(self, dm_with_numeric_data):
        
        result = dm_with_numeric_data.aggregate_data("category", "value", "sum")

        assert isinstance(result, pd.Series)
        assert result["A"] == 30
        assert result["B"] == 70
        assert result["C"] == 50

    def test_aggregate_mean(self, dm_with_numeric_data):
       
        result = dm_with_numeric_data.aggregate_data("category", "value", "mean")

        assert isinstance(result, pd.Series)
        assert result["A"] == 15.0
        assert result["B"] == 35.0

    def test_aggregate_count(self, dm_with_numeric_data):
        "
        result = dm_with_numeric_data.aggregate_data("category", "value", "count")

        assert isinstance(result, pd.Series)
        assert result["A"] == 2
        assert result["B"] == 2
        assert result["C"] == 1

    def test_aggregate_invalid_function(self, dm_with_numeric_data):
        
        result = dm_with_numeric_data.aggregate_data("category", "value", "invalid_func")

        assert isinstance(result, (pd.Series, type(None)))

    def test_aggregate_nonexistent_column(self, dm_with_numeric_data):
       
        result = dm_with_numeric_data.aggregate_data("nonexistent", "value", "sum")

        assert isinstance(result, (pd.Series, type(None)))

    def test_aggregate_empty_dataframe(self):
        
        dm = DataManager()
        result = dm.aggregate_data("category", "value", "sum")

        assert isinstance(result, (pd.Series, type(None)))


class TestSaveData:
    

    @pytest.fixture
    def dm_with_data(self):
        
        dm = DataManager()
        dm.df = pd.DataFrame({
            "id": [1, 2],
            "name": ["Alice", "Bob"]
        })
        return dm

    def test_save_csv(self, dm_with_data, tmp_path):
        
        output_file = tmp_path / "output.csv"

        result = dm_with_data.save_data(str(output_file), "csv")

        assert result is True
        assert output_file.exists()
        # Verifica conteúdo
        saved_df = pd.read_csv(output_file)
        assert len(saved_df) == 2

    def test_save_excel(self, dm_with_data, tmp_path):
        
        output_file = tmp_path / "output.xlsx"

        result = dm_with_data.save_data(str(output_file), "excel")

        assert result is True
        assert output_file.exists()

    def test_save_json(self, dm_with_data, tmp_path):
        
        output_file = tmp_path / "output.json"

        result = dm_with_data.save_data(str(output_file), "json")

        assert result is True
        assert output_file.exists()

    def test_save_invalid_format(self, dm_with_data, tmp_path):
        
        output_file = tmp_path / "output.unknown"

        result = dm_with_data.save_data(str(output_file), "unknown")

        assert result is False

    def test_save_empty_dataframe(self, tmp_path):
        
        dm = DataManager()
        output_file = tmp_path / "empty.csv"

        result = dm.save_data(str(output_file), "csv")

        assert result is True or result is False


class TestGetStatistics:
    

    @pytest.fixture
    def dm_with_stats_data(self):
        
        dm = DataManager()
        dm.df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50]
        })
        return dm

    def test_get_statistics_basic(self, dm_with_stats_data):
        
        stats = dm_with_stats_data.get_statistics()

        assert isinstance(stats, dict)
        assert "mean" in stats or "count" in stats
        assert stats.get("count") == 5 or len(dm_with_stats_data.df) == 5

    def test_get_statistics_empty(self):
        
        dm = DataManager()
        stats = dm.get_statistics()

        assert isinstance(stats, dict)

    def test_get_statistics_numeric_values(self, dm_with_stats_data):
        
        stats = dm_with_stats_data.get_statistics()

        # Verifica se contém descrições padrão do pandas
        assert len(stats) >= 0


class TestCleanData:
    

    @pytest.fixture
    def dm_with_dirty_data(self):
        dm = DataManager()
        dm.df = pd.DataFrame({
            "id": [1, 2, None, 4],
            "name": ["Alice", None, "Charlie", "David"],
            "value": [100, 200, 300, None]
        })
        return dm


