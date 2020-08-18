"""Test ``runway kbenv`` command."""
# pylint: disable=unused-argument
import logging
import sys

import six
from click.testing import CliRunner

from runway._cli import cli

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E


def test_kbenv_install(cd_tmp_path, caplog):
    """Test ``runway kbenv install`` reading version from a file.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.kbenv")
    (cd_tmp_path / ".kubectl-version").write_text(six.u("v1.14.1"))
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "install"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].strip("kubectl path: "))
    assert kb_bin.exists()


def test_kbenv_install_no_version_file(cd_tmp_path, caplog):
    """Test ``runway kbenv install`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "install"])
    assert result.exit_code == 1

    assert "no .kubectl-version file present" in caplog.messages[0]


def test_kbenv_install_version(caplog):
    """Test ``runway kbenv install <version>``.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.kbenv")
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "install", "v1.14.0"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].strip("kubectl path: "))
    assert kb_bin.exists()


def test_kbenv_run_no_version_file(cd_tmp_path, caplog):
    """Test ``runway kbenv run -- --help`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "run", "--", "--help"])
    assert result.exit_code == 1

    assert "no .kubectl-version file present" in caplog.messages[0]


def test_kbenv_run_separator(cd_tmp_path, capfd):
    """Test ``runway kbenv run -- --help``.

    Parsing of command using ``--`` as a seperator between options and args.
    Everything that comes after the seperator should be forwarded on as an arg
    and not parsed as an option by click. This is only required when trying to
    pass options shared with Runway such as ``--help``.

    """
    (cd_tmp_path / ".kubectl-version").write_text(six.u("v1.14.0"))
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "run", "--", "--help"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "runway" not in captured.out
    assert "kubectl <command> --help" in captured.out


def test_kbenv_run_version(cd_tmp_path, capfd):
    """Test ``runway kbenv run version``.

    Parsing of bare command.

    """
    (cd_tmp_path / ".kubectl-version").write_text(six.u("v1.14.0"))
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "run", "version", "--client"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "v1.14.0" in captured.out
