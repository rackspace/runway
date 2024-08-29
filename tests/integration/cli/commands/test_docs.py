"""Test ``runway docs`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from unittest.mock import MagicMock

DOCS_URL = "https://runway.readthedocs.io/"


@patch("click.launch")
def test_docs(mock_launch: MagicMock) -> None:
    """Test docs."""
    runner = CliRunner()
    assert runner.invoke(cli, ["docs"], env={}).exit_code == 0
    mock_launch.assert_called_once_with(DOCS_URL)

    assert runner.invoke(cli, ["docs"], env={"LD_LIBRARY_PATH_ORIG": "something"}).exit_code == 0
    assert mock_launch.call_count == 2
