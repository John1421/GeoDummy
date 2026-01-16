import pytest
import json
import os
import subprocess
import shutil
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from typing import Generator
from werkzeug.exceptions import BadRequest, NotFound

# Assuming ScriptManager is defined in ScriptManager.py
from App.ScriptManager import ScriptManager, layer_manager

class TestScriptManager:
    """
    Senior SDET-level test suite for ScriptManager.
    Fixes previous issues with MagicMock path handling and type comparisons.
    """

    @pytest.fixture
    def mock_deps(self) -> Generator:
        """
        Mocks the external FileManager and LayerManager instances.
        Ensures numeric attributes and path-returning methods return strings, not mocks.
        """
        with patch('App.ScriptManager.file_manager') as mock_fm, \
             patch('App.ScriptManager.layer_manager') as mock_lm:
            
            # Setup default behavior for FileManager
            mock_fm.scripts_dir = "/tmp/scripts"
            mock_fm.execution_dir = "/tmp/exec"
            mock_fm.temp_dir = "/tmp/temp"
            
            # Fix TypeError: Ensure MAX_LAYER_FILE_SIZE is an int, not a Mock
            mock_lm.MAX_LAYER_FILE_SIZE = 100 * 1024 * 1024 
            
            # Fix OSError: Ensure get_layer_path returns a string path
            mock_lm.get_layer_path.return_value = None 
            
            yield mock_fm, mock_lm

    @pytest.fixture
    def script_manager(self, tmp_path: Path, mock_deps: tuple) -> ScriptManager:
        """Initializes ScriptManager with a isolated temporary directory."""
        mock_fm, _ = mock_deps
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        mock_fm.scripts_dir = str(scripts_dir)
        
        # Ensure execution directory exists for run_script tests
        exec_dir = tmp_path / "exec"
        exec_dir.mkdir()
        mock_fm.execution_dir = str(exec_dir)

        return ScriptManager(scripts_metadata='test_metadata.json')

    # --- Execution Tests ---

    @patch('App.ScriptManager.shutil.copy')
    @patch('App.ScriptManager.subprocess.run')
    def test_run_script_success(self, mock_subproc, mock_copy, script_manager: ScriptManager, tmp_path):
        # 1. Setup paths
        # Ensure the 'source' script exists so _validate_script_integrity doesn't fail
        script_id = 'test_script'
        execution_id = 'exec_1'
        
        script_content = "def main(params): print('Hello')\nif __name__ == '__main__': main({})"
        source_script = tmp_path / "source_script.py"
        source_script.write_text(script_content)

        # 2. Setup mock subprocess result
        mock_res = MagicMock(stdout="Hello World", stderr="", returncode=0)
        mock_subproc.return_value = mock_res

        # 3. Execute - we must bypass the internal integrity check or ensure the file exists
        # Since we mocked shutil.copy, we should also mock the validator to avoid FileIO errors
        with patch.object(ScriptManager, '_validate_script_integrity'):
            result = script_manager.run_script(str(source_script), script_id, execution_id, {"layers": []})

            assert result["execution_id"] == execution_id
            assert result["status"] == "success"
            # Change this line:
            assert "layer_ids" in result
            assert "metadatas" in result

    @patch('subprocess.run')
    @patch('shutil.copy')
    def test_run_script_timeout(self, mock_copy, mock_subproc, script_manager: ScriptManager, tmp_path: Path, mock_deps):
        """
        Tests timeout handling.
        Fixes TypeError by ensuring MAX_LAYER_FILE_SIZE is an integer via fixture.
        """
        mock_subproc.side_effect = subprocess.TimeoutExpired(cmd=["python3"], timeout=30)
        dummy_script = tmp_path / "test_script.py"
        dummy_script.write_text("def main(): pass")

        with patch.object(ScriptManager, '_validate_script_integrity'):
            # Ensure output folder check finds nothing to avoid size comparison
            with patch('pathlib.Path.glob', return_value=[]):
                response = script_manager.run_script(str(dummy_script), "test_id", "456", {})
        
        assert response["status"] == "timeout"

    # --- Edge Cases & Internal Helpers ---

    def test_add_script_parsing(self, script_manager: ScriptManager):
        """
        Tests that add_script correctly parses JSON strings.
        """
        # JSON uses lowercase 'true'
        form_data = {
            "config": '{"timeout": 30, "retry": true}',
            "simple_text": "plain_string"
        }
        
        with patch.object(script_manager, 'save_metadata'):
            script_manager.add_script("test_script_1", form_data)
        
        # Verify JSON was parsed into a dictionary, not left as a string
        expected_config = {"timeout": 30, "retry": True}
        assert script_manager.metadata["scripts"]["test_script_1"]["config"] == expected_config
        assert script_manager.metadata["scripts"]["test_script_1"]["simple_text"] == "plain_string"

    def test_add_script_edge_case_empty_form(self, script_manager: ScriptManager):
        """
        Tests behavior with an empty parameters dictionary.
        Covers: Boundary/Edge case for loop iterations.
        """
        script_manager.add_script("script_123", {})
        # The code now adds an empty dict for the script
        assert script_manager.metadata["scripts"]["script_123"] == {}


    # --- Tests for _validate_script_integrity ---

    def test_validate_script_integrity_success(self, tmp_path: Path):
        """
        Tests a perfectly valid script with main() and the __main__ guard.
        Covers the full successful execution path of the validator.
        """
        script_content = (
            "def main(params):\n"
            "    print(params)\n"
            "if __name__ == '__main__':\n"
            "    main({})"
        )
        valid_script = tmp_path / "valid_script.py"
        valid_script.write_text(script_content)

        # Should not raise any exceptions
        ScriptManager._validate_script_integrity(str(valid_script))

    @patch('subprocess.run')
    def test_validate_script_syntax_error(self, mock_run, tmp_path: Path):
        """
        Tests behavior when the script has a Python syntax error.
        Covers: result.returncode != 0 branch.
        """
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stderr = "SyntaxError: invalid syntax"
        mock_run.return_value = mock_res
        
        bad_syntax_script = tmp_path / "bad_syntax.py"
        bad_syntax_script.write_text("invalid python code")

        with pytest.raises(BadRequest) as excinfo:
            ScriptManager._validate_script_integrity(str(bad_syntax_script))
        
        assert "SyntaxError" in str(excinfo.value)

    def test_validate_script_missing_main_definition(self, tmp_path: Path):
        """
        Tests behavior when the 'main' function is not defined.
        Covers: any(isinstance(node, ast.FunctionDef)...) == False branch.
        """
        script_content = "def not_main(): pass"
        script = tmp_path / "no_main.py"
        script.write_text(script_content)

        with pytest.raises(BadRequest) as excinfo:
            ScriptManager._validate_script_integrity(str(script))
        
        assert "must define a function named 'main(params)'" in str(excinfo.value)

    def test_validate_script_missing_guard(self, tmp_path: Path):
        """
        Tests behavior when main() is defined but the __main__ guard is missing.
        Covers: main_called == False branch.
        """
        script_content = "def main(params): pass\nmain({})" # main called, but no if __name__
        script = tmp_path / "no_guard.py"
        script.write_text(script_content)

        with pytest.raises(BadRequest) as excinfo:
            ScriptManager._validate_script_integrity(str(script))
        
        assert "not called under '__main__' guard" in str(excinfo.value)

    def test_validate_script_guard_exists_but_no_call(self, tmp_path: Path):
        """
        Tests behavior when the guard exists but does not actually call main().
        Covers: Deep AST walking branch where 'if' is found but 'Call' to main is not.
        """
        script_content = (
            "def main(params): pass\n"
            "if __name__ == '__main__':\n"
            "    print('Hello')" # Guard exists, but main() isn't called here
        )
        script = tmp_path / "guard_no_call.py"
        script.write_text(script_content)

        with pytest.raises(BadRequest) as excinfo:
            ScriptManager._validate_script_integrity(str(script))
        
        assert "not called under '__main__' guard" in str(excinfo.value)

    def test_validate_script_wrong_guard_comparison(self, tmp_path: Path):
        """
        Tests behavior with a different 'if' condition that isn't the __main__ guard.
        Covers: Edge case where ast.If exists but fails the comparison logic.
        """
        script_content = (
            "def main(params): pass\n"
            "if 1 == 1:\n"
            "    main({})"
        )
        script = tmp_path / "wrong_guard.py"
        script.write_text(script_content)

        with pytest.raises(BadRequest) as excinfo:
            ScriptManager._validate_script_integrity(str(script))
        
        assert "not called under '__main__' guard" in str(excinfo.value)

    def test_prepare_parameters_invalid_dir(self, script_manager: ScriptManager):
        """
        Tests that a BadRequest is raised when the execution input directory does not exist.
        Covers: if not os.path.isdir(execution_dir_input) branch.
        """
        invalid_dir = "/non/existent/path/for/inputs"
        data = {"layers": ["layer1"]}

        with pytest.raises(BadRequest) as excinfo:
            # Accessing private method via name mangling
            script_manager._ScriptManager__prepare_parameters_for_script(data, invalid_dir)
        
        assert "Couldn't locate folder" in str(excinfo.value)

    @patch('App.ScriptManager.shutil.copy')
    @patch('os.path.isdir')
    def test_prepare_parameters_success(self, mock_isdir, mock_copy, script_manager: ScriptManager, mock_deps):
        """
        Tests successful parameter preparation with multiple layers.
        Covers: successful loop iteration, layer path resolution, and file copying.
        """
        _, mock_lm = mock_deps
        mock_isdir.return_value = True
        
        # Setup mock layer paths
        execution_dir = "/tmp/exec/inputs"
        mock_lm.get_layer_path.side_effect = ["/data/layer1.geojson", "/data/layer2.tif"]
        
        data = {"layers": ["id1", "id2"], "other_param": 123}
        
        result = script_manager._ScriptManager__prepare_parameters_for_script(data, execution_dir)
        
        # Verify result structure
        assert len(result["layers"]) == 2
        assert result["other_param"] == 123
        # Verify paths are absolute and point to the execution directory
        assert os.path.basename(result["layers"][0]) == "layer1.geojson"
        assert os.path.dirname(result["layers"][0]).replace("\\", "/") == os.path.abspath(execution_dir).replace("\\", "/")
        
        # Verify shutil.copy was called for each layer
        assert mock_copy.call_count == 2

    @patch('os.path.isdir')
    def test_prepare_parameters_layer_not_found(self, mock_isdir, script_manager: ScriptManager, mock_deps):
        """
        Tests that a NotFound exception is raised if a layer ID cannot be resolved.
        Covers: else branch (layer is None).
        """
        _, mock_lm = mock_deps
        mock_isdir.return_value = True
        mock_lm.get_layer_path.return_value = None
        
        data = {"layers": ["missing_layer"]}
        execution_dir = "/tmp/exec/inputs"

        with pytest.raises(NotFound) as excinfo:
            script_manager._ScriptManager__prepare_parameters_for_script(data, execution_dir)
        
        assert "Layer not found" in str(excinfo.value)

    @patch('os.path.isdir')
    def test_prepare_parameters_empty_layers(self, mock_isdir, script_manager: ScriptManager):
        """
        Tests behavior when the 'layers' key is missing or empty.
        Covers: Edge case - data.get("layers", []) fallback.
        """
        mock_isdir.return_value = True
        data = {"other_stuff": "no_layers_here"}
        execution_dir = "/tmp/exec/inputs"

        result = script_manager._ScriptManager__prepare_parameters_for_script(data, execution_dir)
        
        assert result["layers"] == []
        assert result["other_stuff"] == "no_layers_here"

    @patch('os.path.isfile')
    def test_validate_script_files_all_exist(self, mock_isfile, script_manager: ScriptManager):
        """
        Tests the scenario where all scripts defined in metadata exist on disk.
        Covers: loop execution where 'if not os.path.isfile' is always False, and 
        the final 'if removed_scripts' is False.
        """
        # Setup metadata with existing scripts
        script_manager.metadata = {
            "scripts": {
                "script_a": {"desc": "test"},
                "script_b": {"desc": "test"}
            }
        }
        # Simulate that both files exist
        mock_isfile.return_value = True
        
        with patch.object(script_manager, 'save_metadata') as mock_save:
            script_manager._validate_script_files()
            
            # Assertions
            assert len(script_manager.metadata["scripts"]) == 2
            mock_save.assert_not_called()

    @patch('os.path.isfile')
    def test_validate_script_files_some_missing(self, mock_isfile, script_manager: ScriptManager):
        """
        Tests the scenario where some scripts are missing from the disk.
        Covers: the branch where 'if not os.path.isfile' is True, script deletion,
        and the final 'if removed_scripts' is True (triggering save_metadata).
        """
        # Setup metadata: script_1 exists, script_2 is missing
        script_manager.metadata = {
            "scripts": {
                "script_1": {},
                "script_2": {}
            }
        }
        
        # side_effect returns True for script_1 and False for script_2
        mock_isfile.side_effect = lambda path: "script_1.py" in path
        
        with patch.object(script_manager, 'save_metadata') as mock_save:
            script_manager._validate_script_files()
            
            # Assertions
            assert "script_1" in script_manager.metadata["scripts"]
            assert "script_2" not in script_manager.metadata["scripts"]
            mock_save.assert_called_once()

    def test_validate_script_files_empty_metadata(self, script_manager: ScriptManager):
        """
        Edge case: Tests behavior when the 'scripts' key is empty or missing.
        Covers: The branch where scripts.keys() is empty and the loop does not run.
        """
        # Setup empty metadata
        script_manager.metadata = {"scripts": {}}
        
        with patch.object(script_manager, 'save_metadata') as mock_save:
            script_manager._validate_script_files()
            
            assert script_manager.metadata["scripts"] == {}
            mock_save.assert_not_called()

    @patch('os.path.isfile')
    def test_validate_script_files_none_exist(self, mock_isfile, script_manager: ScriptManager):
        """
        Tests the scenario where none of the scripts defined in metadata exist on disk.
        Covers: full cleanup of the scripts dictionary.
        """
        script_manager.metadata = {
            "scripts": {
                "missing_1": {},
                "missing_2": {}
            }
        }
        # All files are missing
        mock_isfile.return_value = False
        
        with patch.object(script_manager, 'save_metadata') as mock_save:
            script_manager._validate_script_files()
            
            assert len(script_manager.metadata["scripts"]) == 0
            mock_save.assert_called_once()

    def test_load_metadata_success(self, script_manager: ScriptManager):
        """
        Tests successful loading of metadata from a JSON file.
        Verifies that self.metadata is updated and the dictionary is returned.
        """
        mock_data = {"scripts": {"test_id": {"name": "Test Script"}}}
        mock_json_content = json.dumps(mock_data)

        # Mock 'open' to return our JSON string
        with patch("builtins.open", mock_open(read_data=mock_json_content)):
            result = script_manager.load_metadata()

        assert result == mock_data
        assert script_manager.metadata == mock_data

    def test_get_metadata_success(self, script_manager: ScriptManager):
        """
        Tests successful retrieval of metadata for a valid script_id.
        Verifies that _load_metadata is called and the specific script data is returned.
        """
        valid_id = "test_script_001"
        expected_data = {"name": "Test Script", "version": "1.0"}
        mock_metadata = {
            "scripts": {
                valid_id: expected_data
            }
        }

        # Mock _load_metadata to return our controlled dictionary
        with patch.object(ScriptManager, 'load_metadata', return_value=mock_metadata) as mock_load:
            result = script_manager.get_metadata(valid_id)
            
            # Assertions
            assert result == expected_data
            assert result["name"] == "Test Script"
            mock_load.assert_called_once()

    @pytest.mark.parametrize("extension, manager_method", [
        (".zip", "add_shapefile_zip"),
        (".geojson", "add_geojson"),
        (".tif", "add_raster"),
        (".tiff", "add_raster"),
    ])
    def test_add_output_to_existing_layers_success_single(
        self, script_manager: ScriptManager, mock_deps, extension, manager_method
    ):
        """
        Tests successful registration of single-layer outputs (zip, geojson, tif).
        Covers: match cases, and the 'if not isinstance(..., list)' normalization.
        """
        _, mock_lm = mock_deps
        file_path = f"/tmp/output/test_layer{extension}"
        mock_output_id = "layer_123"
        mock_metadata = {"type": "vector"}
        
        # Setup the specific layer_manager method being called
        getattr(mock_lm, manager_method).return_value = (mock_output_id, mock_metadata)

        # Accessing private static method
        ids, meta = script_manager._ScriptManager__add_output_to_existing_layers(file_path)

        assert ids == [mock_output_id]
        assert meta == [mock_metadata]
        assert isinstance(ids, list)
        assert isinstance(meta, list)

    def test_add_output_to_existing_layers_gpkg_list(self, script_manager: ScriptManager, mock_deps):
        """
        Tests Geopackage output which typically returns lists.
        Covers: .gpkg case and bypasses the list normalization (since it's already a list).
        """
        _, mock_lm = mock_deps
        file_path = "/tmp/output/data.gpkg"
        mock_ids = ["l1", "l2"]
        mock_metas = [{"id": "l1"}, {"id": "l2"}]
        mock_lm.add_gpkg_layers.return_value = (mock_ids, mock_metas)

        ids, meta = script_manager._ScriptManager__add_output_to_existing_layers(file_path)

        assert ids == mock_ids
        assert meta == mock_metas

    @patch("os.path.exists")
    @patch("os.remove")
    def test_add_output_to_existing_layers_shp_error(self, mock_remove, mock_exists, script_manager: ScriptManager):
        """
        Tests that .shp files are rejected and deleted if they exist.
        Covers: .shp case, os.path.exists == True branch, and BadRequest exception.
        """
        file_path = "/tmp/output/invalid.shp"
        mock_exists.return_value = True

        with pytest.raises(BadRequest) as excinfo:
            script_manager._ScriptManager__add_output_to_existing_layers(file_path)

        assert "upload shapefiles as a .zip" in str(excinfo.value)
        mock_remove.assert_called_once_with(file_path)

    @patch("os.path.exists")
    @patch("os.remove")
    def test_add_output_to_existing_layers_unsupported_and_missing(self, mock_remove, mock_exists, script_manager: ScriptManager):
        """
        Tests unsupported extensions and ensuring remove isn't called if file doesn't exist.
        Covers: default case (_), os.path.exists == False branch.
        """
        file_path = "/tmp/output/wrong.exe"
        mock_exists.return_value = False

        with pytest.raises(BadRequest) as excinfo:
            script_manager._ScriptManager__add_output_to_existing_layers(file_path)

        assert "extension not supported" in str(excinfo.value)
        mock_remove.assert_not_called()

    def test_add_output_to_existing_layers_case_insensitivity(self, script_manager: ScriptManager, mock_deps):
        """
        Tests that the match statement handles uppercase extensions.
        Covers: .lower() branch logic.
        """
        _, mock_lm = mock_deps
        file_path = "/tmp/output/PHOTO.TIF"
        mock_lm.add_raster.return_value = ("id", "meta")

        ids, _ = script_manager._ScriptManager__add_output_to_existing_layers(file_path)
        assert ids == ["id"]
        mock_lm.add_raster.assert_called_once()

    def test_init_raises_if_scripts_dir_missing(self, mock_deps) -> None:
        """
        Branch: if not os.path.isdir(file_manager.scripts_dir) -> FileNotFoundError.
        """
        mock_fm, _ = mock_deps

        # Point scripts_dir somewhere, but force isdir to return False
        mock_fm.scripts_dir = "/nonexistent/scripts"

        with patch("App.ScriptManager.os.path.isdir", return_value=False):
            with pytest.raises(FileNotFoundError) as excinfo:
                ScriptManager(scripts_metadata="test_metadata.json")

        assert "Script directory does not exist" in str(excinfo.value)
    

    def test_check_script_name_exists_true(self, script_manager: ScriptManager) -> None:
        # Arrange: ensure metadata has a script_123 entry
        script_manager.metadata.setdefault("scripts", {})
        script_manager.metadata["scripts"]["script_123"] = {}
        
        # Act
        result = script_manager.check_script_name_exists("script_123")
        
        # Assert
        assert result is True

    def test_check_script_name_exists_false(self, script_manager: ScriptManager) -> None:
        # Arrange: scripts dict is empty or missing
        script_manager.metadata["scripts"] = {}

        # Act
        result = script_manager.check_script_name_exists("nonexistent")

        # Assert
        assert result is False

    def test_add_script_initializes_scripts_dict(self, script_manager: ScriptManager, tmp_path) -> None:
        """
        Branch: 'scripts' not in self.metadata → self.metadata['scripts'] = {}.
        """
        # Simulate metadata without 'scripts' key
        script_manager.metadata = {}

        metadata_form = {
            "name": "My Script",
            "version": "1.0"
        }

        # Exercise
        script_manager.add_script("script_123", metadata_form)

        # Assertions
        assert "scripts" in script_manager.metadata
        assert "script_123" in script_manager.metadata["scripts"]
        assert script_manager.metadata["scripts"]["script_123"]["name"] == "My Script"
        assert script_manager.metadata["scripts"]["script_123"]["version"] == 1.0

    def test_add_script_does_not_overwrite_existing_scripts(self, script_manager: ScriptManager) -> None:
        """
        Complementary check: branch when 'scripts' already exists.
        """
        script_manager.metadata = {"scripts": {"existing": {"name": "Old"}}}

        metadata_form = {"name": "New Script"}

        script_manager.add_script("new_id", metadata_form)

        assert "existing" in script_manager.metadata["scripts"]
        assert "new_id" in script_manager.metadata["scripts"]

    def test_list_scripts_success(self, script_manager: ScriptManager) -> None:
        """
        Happy path: returns ids and their metadata list.
        """
        # Setup: two scripts registered in in-memory metadata
        script_manager.metadata = {
            "scripts": {
                "s1": {},
                "s2": {},
            }
        }

        # Mock get_metadata so it returns specific values without touching disk
        with patch.object(script_manager, "get_metadata") as mock_get_meta:
            mock_get_meta.side_effect = [
                {"name": "one"},
                {"name": "two"},
            ]

            ids, metas = script_manager.list_scripts()

        assert ids == ["s1", "s2"]
        assert metas == [{"name": "one"}, {"name": "two"}]
        assert mock_get_meta.call_args_list[0].args[0] == "s1"
        assert mock_get_meta.call_args_list[1].args[0] == "s2"

    def test_list_scripts_error_wraps_in_value_error(self, script_manager: ScriptManager) -> None:
        """
        Error in get_metadata is wrapped as ValueError('Error retrieving scripts: ...').
        """
        script_manager.metadata = {"scripts": {"bad": {}}}

        with patch.object(script_manager, "get_metadata") as mock_get_meta:
            mock_get_meta.side_effect = RuntimeError("boom")

            with pytest.raises(ValueError) as excinfo:
                script_manager.list_scripts()

        assert "Error retrieving scripts: boom" in str(excinfo.value)
        mock_get_meta.assert_called_once_with("bad")

    def test_clean_temp_layer_files_removes_existing_files(self, tmp_path: Path) -> None:
        """
        Branch: for layer in layers, os.path.isfile(layer) is True and os.remove is called.
        """
        # Create two temp files, plus one non-existent path
        f1 = tmp_path / "layer1.tif"
        f2 = tmp_path / "layer2.tif"
        f1.write_text("data")
        f2.write_text("data")
        missing = tmp_path / "missing.tif"

        layers = [str(f1), str(f2), str(missing)]

        # Act
        ScriptManager._ScriptManager__clean_temp_layer_files(layers)

        # Assert: existing files removed, missing one ignored
        assert not f1.exists()
        assert not f2.exists()
        assert not missing.exists()

    @patch("App.ScriptManager.file_manager")
    def test_run_script_terminated_status(self, mock_fm, script_manager: ScriptManager, tmp_path: Path) -> None:
        """
        Branch: subprocess.CalledProcessError with returncode == 15 → status 'terminated'.
        """
        mock_fm.execution_dir = str(tmp_path)

        # Real script file (content irrelevant because subprocess.run is patched)
        script_path = tmp_path / "dummy.py"
        script_path.write_text("print('hello')")

        script_id = "script1"
        execution_id = "exec1"
        data = {}

        with patch.object(script_manager, "_validate_script_integrity"), \
             patch.object(script_manager, "_ScriptManager__prepare_parameters_for_script", return_value=data), \
             patch("App.ScriptManager.subprocess.run") as mock_run:

            err = subprocess.CalledProcessError(
                returncode=15,
                cmd=["python"],
                output="",
                stderr="terminated",
            )
            mock_run.side_effect = err

            result = script_manager.run_script(str(script_path), script_id, execution_id, data)

        assert result["status"] == "terminated"

    @patch("App.ScriptManager.file_manager")
    def test_run_script_failure_status(self, mock_fm, script_manager: ScriptManager, tmp_path: Path) -> None:
        """
        Branch: subprocess.CalledProcessError with returncode != 15 → status 'failure'.
        """
        mock_fm.execution_dir = str(tmp_path)

        script_path = tmp_path / "dummy2.py"
        script_path.write_text("print('hello')")

        script_id = "script2"
        execution_id = "exec2"
        data = {}

        with patch.object(script_manager, "_validate_script_integrity"), \
             patch.object(script_manager, "_ScriptManager__prepare_parameters_for_script", return_value=data), \
             patch("App.ScriptManager.subprocess.run") as mock_run:

            err = subprocess.CalledProcessError(
                returncode=1,
                cmd=["python"],
                output="",
                stderr="error",
            )
            mock_run.side_effect = err

            result = script_manager.run_script(str(script_path), script_id, execution_id, data)

        assert result["status"] == "failure"

    @patch("App.ScriptManager.file_manager")
    def test_delete_script_success(self, mock_fm, script_manager: ScriptManager, tmp_path: Path) -> None:
        """
        Happy path:
        - script_id present in metadata -> removed and metadata saved.
        - script file removed from scripts_dir.
        """
        script_id = "script_ok"

        # Point scripts_dir to a temp dir and create a fake script file
        mock_fm.scripts_dir = str(tmp_path)
        script_path = tmp_path / f"{script_id}.py"
        script_path.write_text("print('hello')")

        # Metadata contains the script
        script_manager.metadata = {"scripts": {script_id: {"name": "test"}}}

        with patch.object(script_manager, "save_metadata") as mock_save:
            script_manager.delete_script(script_id)

        # Metadata entry removed
        assert script_id not in script_manager.metadata["scripts"]
        mock_save.assert_called_once()

        # File removed
        assert not script_path.exists()


    @patch("App.ScriptManager.file_manager")
    def test_delete_script_raises_value_error_on_failure(self, mock_fm, script_manager: ScriptManager, tmp_path: Path) -> None:
        """
        Error path:
        - any exception in delete logic is wrapped as ValueError.
        """
        script_id = "script_fail"

        mock_fm.scripts_dir = str(tmp_path)
        script_path = tmp_path / f"{script_id}.py"
        script_path.write_text("print('hello')")

        # Ensure script_id in metadata so branch is taken
        script_manager.metadata = {"scripts": {script_id: {"name": "test"}}}

        # Make os.remove fail
        with patch("App.ScriptManager.os.remove") as mock_remove:
            mock_remove.side_effect = OSError("disk error")

            with pytest.raises(ValueError) as excinfo:
                script_manager.delete_script(script_id)

        assert f"Error deleting script {script_id}: disk error" in str(excinfo.value)
        mock_remove.assert_called_once_with(os.path.join(mock_fm.scripts_dir, f"{script_id}.py"))

    @patch("App.ScriptManager.file_manager")
    def test_run_script_processes_output_files(self, mock_fm, script_manager: ScriptManager, tmp_path: Path) -> None:
        """
        Branch: for file_path in output_files, is_file() True,
        size under limit, __add_output_to_existing_layers called.
        """
        mock_fm.execution_dir = str(tmp_path)

        # Dummy script file
        script_path = tmp_path / "dummy.py"
        script_path.write_text("print('hello')")

        script_id = "script_out"
        execution_id = "exec_out"
        data = {"layers": []}

        # Prepare expected output file inside the outputs folder created by run_script
        outputs_root = tmp_path / str(execution_id) / "outputs"
        outputs_root.mkdir(parents=True, exist_ok=True)
        out_file = outputs_root / "result.geojson"
        out_file.write_text("dummy")

        # Patch non-tested internals + os.path.getsize to keep under limit
        with patch.object(script_manager, "_validate_script_integrity"), \
             patch.object(script_manager, "_ScriptManager__prepare_parameters_for_script", return_value=data), \
             patch("App.ScriptManager.subprocess.run") as mock_run, \
             patch("App.ScriptManager.os.path.getsize", return_value=100), \
             patch.object(script_manager, "_ScriptManager__clean_temp_layer_files") as mock_clean, \
             patch.object(script_manager, "_ScriptManager__add_output_to_existing_layers") as mock_add:

            # Simulate successful subprocess
            proc = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="OK", stderr="")
            mock_run.return_value = proc

            # __add_output_to_existing_layers returns one layer_id + metadata
            mock_add.return_value = (["layer1"], [{"name": "Layer 1"}])

            result = script_manager.run_script(str(script_path), script_id, execution_id, data)

        # Verify loop processed our output file
        mock_add.assert_called_once()
        assert result["status"] == "success"
        assert result["layer_ids"] == ["layer1"]
        assert result["metadatas"] == [{"name": "Layer 1"}]
        mock_clean.assert_called_once_with([])

    def test_run_script_output_file_too_large_raises(
        self, script_manager: ScriptManager, tmp_path: Path, mock_deps
    ) -> None:
        """
        Branch: filesize_bytes > layer_manager.MAX_LAYER_FILE_SIZE → BadRequest.
        """
        mock_fm, mock_lm = mock_deps

        # Make limit small for this test
        mock_lm.MAX_LAYER_FILE_SIZE = 100  # bytes

        # Dummy script file
        script_path = tmp_path / "dummy_big.py"
        script_path.write_text("print('hello')")

        script_id = "big_script"
        execution_id = "exec_big"
        data = {"layers": []}

        # Ensure execution_dir points to our tmp path
        mock_fm.execution_dir = str(tmp_path)

        # Prepare outputs folder and one output file
        outputs_root = tmp_path / str(execution_id) / "outputs"
        outputs_root.mkdir(parents=True, exist_ok=True)
        out_file = outputs_root / "huge_result.tif"
        out_file.write_text("x")

        with patch.object(ScriptManager, "_validate_script_integrity"), \
             patch.object(ScriptManager, "_ScriptManager__prepare_parameters_for_script", return_value=data), \
             patch("App.ScriptManager.subprocess.run") as mock_run, \
             patch("App.ScriptManager.os.path.getsize", return_value=101), \
             patch.object(ScriptManager, "_ScriptManager__clean_temp_layer_files"), \
             patch.object(ScriptManager, "_ScriptManager__add_output_to_existing_layers") as mock_add:

            proc = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="OK", stderr="")
            mock_run.return_value = proc

            with pytest.raises(BadRequest) as excinfo:
                script_manager.run_script(str(script_path), script_id, execution_id, data)

        # We should fail due to size and never process the layer
        mock_add.assert_not_called()
        assert "huge_result.tif exceeds the maximum allowed size" in str(excinfo.value)

    @patch("os.path.exists")
    @patch("os.remove")
    def test_add_output_to_existing_layers_unsupported_and_existing(
        self, mock_remove, mock_exists, script_manager: ScriptManager
    ):
        """
        Tests unsupported extensions and ensures remove IS called if file exists.
        Covers: default case (_), os.path.exists == True branch.
        """
        file_path = "/tmp/output/wrong.exe"
        mock_exists.return_value = True

        with pytest.raises(BadRequest) as excinfo:
            script_manager._ScriptManager__add_output_to_existing_layers(file_path)

        assert "extension not supported" in str(excinfo.value)
        mock_remove.assert_called_once_with(file_path)