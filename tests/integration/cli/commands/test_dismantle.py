"""Test ``runway dismantle``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner
from mock import Mock

from runway._cli import cli
from runway._cli.commands import destroy

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture, MonkeyPatch

    from ...conftest import CpConfigTypeDef


def test_dismantle(
    caplog: LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test dismantle."""
    cp_config("min_required", cd_tmp_path)
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.dismantle")
    mock_forward = Mock()
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
