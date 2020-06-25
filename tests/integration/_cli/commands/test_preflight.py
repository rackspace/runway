"""Test ``runway preflight``."""
import logging

from click.testing import CliRunner
from mock import MagicMock

from runway._cli import cli
from runway._cli.commands import test


def test_preflight(caplog, monkeypatch):
    """Test ``runway preflight``."""
    caplog.set_level(logging.DEBUG, logger='runway.cli.commands.preflight')
    mock_forward = MagicMock()
    monkeypatch.setattr('click.Context.forward', mock_forward)

    runner = CliRunner()
    result = runner.invoke(cli, ['preflight',
                                 '--deploy-environment', 'test'])
    assert result.exit_code == 0
    assert 'forwarding to test...' in caplog.messages
    mock_forward.assert_called_once_with(test, deploy_environment='test')
