"""Test ``runway docs`` command."""
from click.testing import CliRunner
from mock import patch

from runway._cli import cli

DOCS_URL = "https://docs.onica.com/projects/runway/"


@patch("click.launch")
def test_docs(mock_launch):
    """Test docs."""
    runner = CliRunner()
    assert runner.invoke(cli, ["docs"], env={}).exit_code == 0
    mock_launch.assert_called_once_with(DOCS_URL)

    assert (
        runner.invoke(
            cli, ["docs"], env={"LD_LIBRARY_PATH_ORIG": "something"}
        ).exit_code
        == 0
    )
    assert mock_launch.call_count == 2
