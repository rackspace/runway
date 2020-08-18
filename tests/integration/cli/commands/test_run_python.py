"""Test ``runway run-python`` command."""
import six
from click.testing import CliRunner

from runway._cli import cli


def test_run_python(cd_tmp_path):
    """Test ``runway run-python hello_world.py``."""
    # TODO remove use of six when dropping python 2
    (cd_tmp_path / "hello_world.py").write_text(
        six.u("if __name__ == '__main__': print('hello world')")
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["run-python", "hello_world.py"])
    assert result.exit_code == 0
    assert "hello world" in result.output
