"""Test runway.core.providers.aws._cli."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from runway.core.providers.aws import cli

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.aws._cli"


def test_cli(caplog: LogCaptureFixture, mocker: MockerFixture) -> None:
    """Test cli."""
    caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.cli")
    mock_clidriver = mocker.patch(f"{MODULE}.create_clidriver")
    mock_clidriver.return_value = mock_clidriver
    mock_clidriver.main.return_value = 0

        assert not cli(["test"])
        assert "passing command to awscli: test" in caplog.messages
        mock_clidriver.assert_called_once_with()
        mock_clidriver.main.assert_called_once_with(["test"])


def test_cli_non_zero(mocker: MockerFixture) -> None:
    """Test cli with non-zero exit code."""
    mock_clidriver = mocker.patch(f"{MODULE}.create_clidriver")
    mock_clidriver.return_value = mock_clidriver
    mock_clidriver.main.return_value = 1

        with pytest.raises(RuntimeError) as excinfo:
            assert cli(["test"])
        assert str(excinfo.value) == "AWS CLI exited with code 1"
