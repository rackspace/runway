"""Test ``runway schema cfngin`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli
from runway.config.models.cfngin import CfnginConfigDefinitionModel

if TYPE_CHECKING:
    from pathlib import Path


def test_schema_cfngin() -> None:
    """Test ``runway schema cfngin``."""
    result = CliRunner().invoke(cli, ["schema", "cfngin"])
    assert result.exit_code == 0
    assert result.output == CfnginConfigDefinitionModel.schema_json(indent=4) + "\n"


def test_schema_cfngin_indent() -> None:
    """Test ``runway schema cfngin --indent 2``."""
    result = CliRunner().invoke(cli, ["schema", "cfngin", "--indent", "2"])
    assert result.exit_code == 0
    assert result.output == CfnginConfigDefinitionModel.schema_json(indent=2) + "\n"


def test_schema_cfngin_output(cd_tmp_path: Path) -> None:
    """Test ``runway schema cfngin --output cfngin-schema.json``."""
    file_path = cd_tmp_path / "cfngin-schema.json"
    result = CliRunner().invoke(cli, ["schema", "cfngin", "--output", file_path.name])
    assert result.exit_code == 0
    assert str(file_path) in result.output
    assert file_path.is_file()
    assert file_path.read_text() == CfnginConfigDefinitionModel.schema_json(indent=4) + "\n"
