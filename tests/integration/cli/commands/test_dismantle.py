"""Test ``runway dismantle``."""
import logging

from click.testing import CliRunner
from mock import MagicMock

from runway._cli import cli
from runway._cli.commands import destroy


def test_dismantle(caplog, cd_tmp_path, cp_config, monkeypatch):
    """Test dismantle."""
    cp_config("min_required", cd_tmp_path)
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.dismantle")
    mock_forward = MagicMock()
    monkeypatch.setattr("click.Context.forward", mock_forward)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dismantle",
            "--ci",
            "--deploy-environment",
            "test",
            "--no-color",
            "--tag",
            "tag1",
            "--tag",
            "tag2",
        ],
    )
    assert result.exit_code == 0
    assert "forwarding to destroy..." in caplog.messages
    mock_forward.assert_called_once_with(
        destroy,
        ci=True,
        debug=0,
        deploy_environment="test",
        no_color=True,
        tags=("tag1", "tag2"),
        verbose=False,
    )
