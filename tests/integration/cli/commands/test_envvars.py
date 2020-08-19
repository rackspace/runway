"""Test ``runway envvars``."""
import logging
import sys

import pytest
from click.testing import CliRunner
from mock import MagicMock

from runway._cli import cli

POSIX_OUTPUT = (
    'export TEST_VAR_01="deployment_1"\n'
    'export TEST_VAR_SHARED="deployment_2"\n'
    'export TEST_VAR_02="deployment_2"\n'
)
PSH_OUTPUT = (
    '$env:TEST_VAR_01 = "deployment_1"\n'
    '$env:TEST_VAR_SHARED = "deployment_2"\n'
    '$env:TEST_VAR_02 = "deployment_2"\n'
)


@pytest.mark.skipif(sys.version_info.major < 3, reason="python 2 dicts are not ordered")
def test_envvars(cd_tmp_path, cp_config, monkeypatch):
    """Test envvars."""
    monkeypatch.setattr("platform.system", MagicMock(return_value="Darwin"))
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["envvars"])
    assert result.exit_code == 0
    assert result.output == POSIX_OUTPUT


@pytest.mark.skipif(sys.version_info.major < 3, reason="python 2 dicts are not ordered")
def test_envvar_windows(cd_tmp_path, cp_config, monkeypatch):
    """Test envvars for Windows."""
    monkeypatch.setattr("platform.system", MagicMock(return_value="Windows"))
    monkeypatch.delenv("MSYSTEM", raising=False)
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result0 = runner.invoke(cli, ["envvars"])
    assert result0.exit_code == 0
    assert result0.output == PSH_OUTPUT

    monkeypatch.setenv("MSYSTEM", "MINGW")
    result1 = runner.invoke(cli, ["envvars"])
    assert result1.output == POSIX_OUTPUT


def test_envvars_no_config(caplog, cd_tmp_path):
    """Test envvars with no config in the directory or parent."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["envvars"])
    assert result.exit_code == 1

    template = (
        "Runway config file was not found. Looking for one of "
        "['runway.yml', 'runway.yaml'] in {path}"
    )
    assert template.format(path=cd_tmp_path) in caplog.messages
    assert template.format(path=cd_tmp_path.parent) in caplog.messages


def test_envvars_no_env_vars(caplog, cd_tmp_path, cp_config):
    """Test envvars with no env_vars in the config."""
    caplog.set_level(logging.ERROR, logger="runway")
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["envvars"])
    assert result.exit_code == 1
    assert (
        "No env_vars defined in %s" % str(cd_tmp_path / "runway.yml") in caplog.messages
    )
