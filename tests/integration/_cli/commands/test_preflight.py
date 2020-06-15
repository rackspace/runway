"""Test ``runway preflight``."""
import logging

import six
import yaml
from click.testing import CliRunner

from runway._cli import cli


SUCCESS = {
    'name': 'success',
    'type': 'script',
    'args': {
        'commands': ['echo "Hello world"']
    }
}


def test_preflight(cd_tmp_path, caplog):
    """Test ``runway preflight``."""
    caplog.set_level(logging.DEBUG, logger='runway._cli.commands.preflight')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['preflight'])
    assert result.exit_code == 0
    assert 'forwarding to test...' in caplog.messages
