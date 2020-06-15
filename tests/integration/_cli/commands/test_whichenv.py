"""Test ``runway whichenv``."""
import six
import yaml
from click.testing import CliRunner

from runway._cli import cli


def test_whichenv(cd_tmp_path):
    """Test ``runway whichenv``."""
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'ignore_git_branch': True})))
    runner = CliRunner()
    result = runner.invoke(cli, ['whichenv'], env={})
    assert result.exit_code == 0
    assert result.output == cd_tmp_path.name + '\n'
