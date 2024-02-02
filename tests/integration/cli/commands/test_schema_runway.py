"""Test ``runway schema runway`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli
from runway.config.models.runway import RunwayConfigDefinitionModel

if TYPE_CHECKING:
    from pathlib import Path


def test_schema_runway() -> None:
    """Test ``runway schema runway``."""
    result = CliRunner().invoke(cli, ["schema", "runway"])
    assert result.exit_code == 0
    assert result.output == RunwayConfigDefinitionModel.schema_json(indent=4) + "\n"


def test_schema_runway_indent() -> None:
    """Test ``runway schema runway --indent 2``."""
    result = CliRunner().invoke(cli, ["schema", "runway", "--indent", "2"])
    assert result.exit_code == 0
    assert result.output == RunwayConfigDefinitionModel.schema_json(indent=2) + "\n"


def test_schema_runway_output(cd_tmp_path: Path) -> None:
    """Test ``runway schema runway --output runway-schema.json``."""
    file_path = cd_tmp_path / "runway-schema.json"
    result = CliRunner().invoke(cli, ["schema", "runway", "--output", file_path.name])
    assert result.exit_code == 0
    assert str(file_path) in result.output
    assert file_path.is_file()
    assert (
        file_path.read_text()
        == RunwayConfigDefinitionModel.schema_json(indent=4) + "\n"
    )
