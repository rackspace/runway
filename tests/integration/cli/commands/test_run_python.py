"""Test ``runway run-python`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path


def test_run_python(cd_tmp_path: Path) -> None:
    """Test ``runway run-python hello_world.py``."""
    (cd_tmp_path / "hello_world.py").write_text(
        "if __name__ == '__main__': print('hello world')"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["run-python", "hello_world.py"])
    assert result.exit_code == 0
    assert "hello world" in result.output
