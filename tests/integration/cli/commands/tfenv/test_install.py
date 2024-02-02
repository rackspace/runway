"""Test ``runway tfenv install`` command."""

# pylint: disable=unused-argument
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from runway._cli import cli
from runway.env_mgr.tfenv import TFEnvManager

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True, scope="function")
def patch_versions_dir(mocker: MockerFixture, tmp_path: Path) -> None:
    """Patch TFEnvManager.versions_dir."""
    mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)


def test_tfenv_install(cd_tmp_path: Path, caplog: LogCaptureFixture) -> None:
    """Test ``runway tfenv install`` reading version from a file.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.tfenv")
    (cd_tmp_path / ".terraform-version").write_text("0.12.0")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install"])
    assert result.exit_code == 0

    tf_bin = Path(caplog.messages[-1].replace("terraform path: ", ""))
    assert tf_bin.exists()


def test_tfenv_install_no_version_file(
    cd_tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Test ``runway tfenv install`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install"])
    assert result.exit_code == 1

    assert "unable to find a .terraform-version file" in "\n".join(caplog.messages)


def test_tfenv_install_version(caplog: LogCaptureFixture) -> None:
    """Test ``runway tfenv install <version>``.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.tfenv")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "install", "0.12.1"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].replace("terraform path: ", ""))
    assert kb_bin.exists()
