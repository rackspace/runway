"""Test runway.config.components.runway._variables_def."""

# pyright: basic
from pathlib import Path

import pytest
import yaml

from runway.config.components.runway import RunwayVariablesDefinition
from runway.exceptions import VariablesFileNotFound


class TestRunwayVariablesDefinition:
    """Test runway.config.components.runway._variables_def.RunwayVariablesDefinition."""

    def test_init_no_file(self, cd_tmp_path: Path) -> None:
        """Test init with no file."""
        assert not RunwayVariablesDefinition.parse_obj({"sys_path": cd_tmp_path})

    @pytest.mark.parametrize(
        "filename", ("runway.variables.yml", "runway.variables.yaml")
    )
    def test_init_autofind_file(self, cd_tmp_path: Path, filename: str) -> None:
        """Test init autofind file."""
        data = {"key": "val"}
        (cd_tmp_path / filename).write_text(yaml.dump(data))
        (cd_tmp_path / "runway.yml").touch()
        assert (
            RunwayVariablesDefinition.parse_obj({"sys_path": cd_tmp_path})["key"]
            == "val"
        )

    def test_init_defined_file_path(self, cd_tmp_path: Path) -> None:
        """Test init with file_path."""
        data = {"key": "val"}
        file_path = cd_tmp_path / "anything.yml"
        file_path.write_text(yaml.dump(data))
        (cd_tmp_path / "runway.yml").touch()
        assert (
            RunwayVariablesDefinition.parse_obj({"file_path": file_path})["key"]
            == "val"
        )

    def test_init_defined_file_path_no_found(self, cd_tmp_path: Path) -> None:
        """Test init with file_path not found."""
        file_path = cd_tmp_path / "anything.yml"
        with pytest.raises(VariablesFileNotFound) as excinfo:
            RunwayVariablesDefinition.parse_obj({"file_path": file_path})
        assert excinfo.value.message.endswith(str(file_path))

    def test_parse_obj(self, cd_tmp_path: Path) -> None:
        """Test parse_obj."""
        obj = RunwayVariablesDefinition.parse_obj({"sys_path": cd_tmp_path})
        assert isinstance(obj, RunwayVariablesDefinition)
