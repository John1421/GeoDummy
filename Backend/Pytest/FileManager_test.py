from unittest.mock import patch
import pytest
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from App.FileManager import FileManager

class TestFileManager:
    """
    Test suite for the FileManager class, covering file operations 
    such as copying, moving, and exception handling for invalid paths.
    """

    @pytest.fixture(autouse=True)
    def setup_fm(self, tmp_path: Path) -> None:
        """
        Fixture to initialize directories and the FileManager instance.
        Executed automatically before each test method.
        """
        self.src_dir = tmp_path / "src"
        self.dest_dir = tmp_path / "dest"
        self.src_dir.mkdir()
        self.dest_dir.mkdir()
        
        # Initialize FileManager with string paths as required by its constructor
        self.fm = FileManager(layers_dir=str(self.src_dir), temp_dir=str(self.dest_dir))

    def _create_dummy_geojson(self, filename: str) -> Path:
        """Helper method to create a valid GeoJSON file for testing."""
        file_path = self.src_dir / filename
        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
        gdf.to_file(file_path, driver='GeoJSON')
        return file_path
    
    def test_move_file_shutil_failure_raises_value_error(self) -> None:
        """
        Branch: exception inside shutil.move triggers
        'Error moving file: ...' ValueError.
        """
        # Create a real source file so validation passes
        src_file = self._create_dummy_geojson("test_move_fail.geojson")

        with patch("App.FileManager.shutil.move") as mock_move:
            # Simulate a low-level failure during move
            mock_move.side_effect = RuntimeError("disk error")

            with pytest.raises(ValueError) as excinfo:
                self.fm.move_file(str(src_file), str(self.dest_dir))

        assert "Error moving file: disk error" in str(excinfo.value)
        mock_move.assert_called_once_with(str(src_file), str(self.dest_dir))

    def test_copy_file_success(self) -> None:
        """Test that a file is successfully copied and the source remains intact."""
        src_file = self._create_dummy_geojson("test_copy.geojson")
        
        # Execution
        result = self.fm.copy_file(str(src_file), str(self.dest_dir))
        
        # Assertions
        assert result is True
        assert (self.dest_dir / "test_copy.geojson").exists()
        assert src_file.exists()

    def test_move_file_success(self) -> None:
        """Test that a file is successfully moved and the source is deleted."""
        src_file = self._create_dummy_geojson("test_move.geojson")
        
        # Execution
        result = self.fm.move_file(str(src_file), str(self.dest_dir))
        
        # Assertions
        assert result is True
        assert (self.dest_dir / "test_move.geojson").exists()
        assert not src_file.exists()

    def test_copy_existing_destination_raises(self) -> None:
        """Edge Case: Test that copying fails if the destination file already exists."""
        filename = "conflict.txt"
        src_file = self.src_dir / filename
        src_file.write_text("source content")
        
        existing_file = self.dest_dir / filename
        existing_file.write_text("existing content")

        # Assertion: Should raise ValueError on conflict
        with pytest.raises(ValueError):
            self.fm.copy_file(str(src_file), str(self.dest_dir))

    def test_move_invalid_source_raises(self) -> None:
        """Edge Case: Test that moving a non-existent source file raises a ValueError."""
        fake_source = self.src_dir / "does_not_exist.txt"

        # Assertion: Should raise ValueError for missing source
        with pytest.raises(ValueError):
            self.fm.move_file(str(fake_source), str(self.dest_dir))
    
    def test_copy_file_shutil_failure_raises_value_error(self) -> None:
        """
        Branch: exception inside shutil.copy triggers
        'Error copying file: ...' ValueError.
        """
        # Create a real source file so __validate_paths_and_file passes
        src_file = self._create_dummy_geojson("test_copy_fail.geojson")

        with patch("App.FileManager.shutil.copy") as mock_copy:
            mock_copy.side_effect = RuntimeError("disk error")

            with pytest.raises(ValueError) as excinfo:
                self.fm.copy_file(str(src_file), str(self.dest_dir))

        assert "Error copying file: disk error" in str(excinfo.value)
        # Destination path is dest_dir / filename, as in implementation
        expected_dest = str(self.dest_dir / "test_copy_fail.geojson")
        mock_copy.assert_called_once_with(str(src_file), expected_dest)

    def test_validate_paths_invalid_destination_path_type_raises(self) -> None:
        """
        Branch: destination_path is not a string → 'Invalid destination path'.
        """
        # Create a valid source file so source_path validation passes
        src_file = self._create_dummy_geojson("test_invalid_dest.geojson")

        # destination_path is not a string (e.g. an int)
        with pytest.raises(ValueError) as excinfo:
            # copy_file calls __validate_paths_and_file internally
            self.fm.copy_file(str(src_file), 123)  # type: ignore[arg-type]

        assert "Invalid destination path" in str(excinfo.value)

    def test_validate_paths_invalid_destination_not_directory_raises(self) -> None:
        """
        Branch: destination_path is a string but not an existing directory.
        """
        src_file = self._create_dummy_geojson("test_invalid_dest_dir.geojson")

        # Use a path that does not exist as a directory
        fake_dest = str(self.src_dir / "not_a_dir")

        with pytest.raises(ValueError) as excinfo:
            self.fm.copy_file(str(src_file), fake_dest)

        assert "Invalid destination path" in str(excinfo.value)