"""Test ``runway tfenv`` command."""
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


def test_tfenv_install(cd_tmp_path, caplog):
    """Test ``runway tfenv install`` reading version from a file.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.tfenv")
    (cd_tmp_path / ".terraform-version").write_text(six.u("0.12.0"))
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install"])
    assert result.exit_code == 0

    tf_bin = Path(caplog.messages[-1].strip("terraform path: "))
    assert tf_bin.exists()


def test_tfenv_install_no_version_file(cd_tmp_path, caplog):
    """Test ``runway tfenv install`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install"])
    assert result.exit_code == 1

    assert "unable to find a .terraform-version file" in "\n".join(caplog.messages)


def test_tfenv_install_version(caplog):
    """Test ``runway tfenv install <version>``.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.tfenv")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install", "0.12.1"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].strip("terraform path: "))
    assert kb_bin.exists()


def test_tfenv_run_no_version_file(cd_tmp_path, caplog):
    """Test ``runway tfenv run -- --help`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--", "--help"])
    assert result.exit_code == 1

    assert "unable to find a .terraform-version file" in "\n".join(caplog.messages)


def test_tfenv_run_separator(cd_tmp_path, capfd):
    """Test ``runway tfenv run -- --help``.

    Parsing of command using ``--`` as a seperator between options and args.
    Everything that comes after the seperator should be forwarded on as an arg
    and not parsed as an option by click. This is only required when trying to
    pass options shared with Runway such as ``--help``.

    """
    (cd_tmp_path / ".terraform-version").write_text(six.u("0.12.0"))
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--", "--help"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "runway" not in captured.out
    assert "terraform [-version] [-help] <command> [args]" in captured.out


def test_tfenv_run_version(cd_tmp_path, capfd):
    """Test ``runway tfenv run --version``.

    Parsing of bare command.

    """
    version = "0.12.0"
    (cd_tmp_path / ".terraform-version").write_text(six.u(version))
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--version"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "Terraform v{}".format(version) in captured.out
