"""Test runway.core.providers.aws._cli."""
import logging

import pytest
from mock import patch

from runway.core.providers.aws import cli

MODULE = "runway.core.providers.aws._cli"


@patch(MODULE + ".create_clidriver")
def test_cli(mock_clidriver, caplog):
    """Test cli."""
    caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.cli")
    mock_clidriver.return_value = mock_clidriver
    mock_clidriver.main.return_value = 0

    assert not cli(["test"])
    assert "passing command to awscli: test" in caplog.messages
    mock_clidriver.assert_called_once_with()
    mock_clidriver.main.assert_called_once_with(["test"])


@patch(MODULE + ".create_clidriver")
def test_cli_non_zero(mock_clidriver):
    """Test cli with non-zero exit code."""
    mock_clidriver.return_value = mock_clidriver
    mock_clidriver.main.return_value = 1

    with pytest.raises(RuntimeError) as excinfo:
        assert cli(["test"])
    assert str(excinfo.value) == "AWS CLI exited with code 1"
