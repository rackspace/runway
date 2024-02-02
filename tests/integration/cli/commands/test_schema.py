"""Test ``runway schema`` command."""

from __future__ import annotations

from click.testing import CliRunner

from runway._cli import cli


def test_schema() -> None:
    """Test schema."""
    result = CliRunner().invoke(cli, ["schema"])
    assert result.exit_code == 0
