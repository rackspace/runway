"""Test ``runway taxi``."""
import logging

from click.testing import CliRunner
from mock import MagicMock

from runway._cli import cli
from runway._cli.commands import plan


def test_taxi(caplog, cd_tmp_path, cp_config, monkeypatch):
    """Test taxi."""
    cp_config("min_required", cd_tmp_path)
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.taxi")
    mock_forward = MagicMock()
    monkeypatch.setattr("click.Context.forward", mock_forward)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "taxi",
            "--ci",
            "--deploy-environment",
            "test",
            "--tag",
            "tag1",
            "--tag",
            "tag2",
        ],
    )
    assert result.exit_code == 0
    assert "forwarding to plan..." in caplog.messages
    mock_forward.assert_called_once_with(
        plan,
        ci=True,
        debug=0,
        deploy_environment="test",
        no_color=False,
        tags=("tag1", "tag2"),
        verbose=False,
    )
