"""Test ``runway taxi``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock

from click.testing import CliRunner

from runway._cli import cli
from runway._cli.commands import plan

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from ...conftest import CpConfigTypeDef


def test_taxi(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test taxi."""
    cp_config("min_required", cd_tmp_path)
    caplog.set_level(logging.DEBUG, logger="runway.cli.commands.taxi")
    mock_forward = Mock()
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
