"""Test runway.commands.runway.envvars."""
from contextlib import contextmanager

import pytest
from mock import MagicMock

from runway.commands.runway.envvars import select_region

MODULE = 'runway.commands.runway.envvars'


@contextmanager
def does_not_raise():
    """Use for conditional pytest.raises when using parametrize."""
    yield


@pytest.mark.wip
@pytest.mark.parametrize('regions, mock_input, expected, exception', [
    (['us-east-1'], MagicMock(), 'us-east-1', does_not_raise()),
    (['us-east-1', 'us-west-2'], MagicMock(return_value='1'), 'us-east-1',
     does_not_raise()),
    (['us-east-1', 'us-west-2'], MagicMock(return_value='2'), 'us-west-2',
     does_not_raise()),
    (['us-east-1', 'us-west-2'], MagicMock(return_value='3'), None,
     pytest.raises(SystemExit)),
    (['us-east-1', 'us-west-2'], MagicMock(return_value='all'), None,
     pytest.raises(SystemExit)),
    (['us-east-1', 'us-west-2'], MagicMock(return_value=''), None,
     pytest.raises(SystemExit))
])
def test_select_region(regions, mock_input, expected, exception, monkeypatch,
                       runway_context):
    """Test select_region."""
    runway_context.env_vars.pop('AWS_DEFAULT_REGION', None)
    runway_context.env_vars.pop('AWS_REGION', None)
    monkeypatch.setattr(MODULE + '.input', mock_input)
    with exception:
        assert select_region(runway_context, regions)

    if expected:
        assert runway_context.env_region == expected
        assert runway_context.env_vars['AWS_DEFAULT_REGION'] == expected
        assert runway_context.env_vars['AWS_REGION'] == expected

    if len(regions) > 1:
        mock_input.assert_called_once()
    else:
        mock_input.assert_not_called()
