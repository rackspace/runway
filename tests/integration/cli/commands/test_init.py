"""Test ``runway init`` command."""
from __future__ import annotations

from click.testing import CliRunner

from runway._cli import cli


def test_init() -> None:
    """Test ``runway init``."""
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0
