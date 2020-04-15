"""Test runway.commands.runway_command."""
import os

import pytest
from git import InvalidGitRepositoryError
from mock import MagicMock, call, patch

from runway.commands.runway_command import (get_env, get_env_from_branch,
                                            get_env_from_directory,
                                            get_env_from_user)
from runway.util import environ


@patch('git.Repo')
@patch('runway.commands.runway_command.get_env_from_branch')
@patch('runway.commands.runway_command.get_env_from_directory')
def test_get_env(mock_env_dir, mock_env_branch, mock_git_repo):
    """Test runway.commands.runway_command.get_env."""
    mock_repo = MagicMock()
    mock_repo.active_branch.name = 'git_branch'
    mock_git_repo.return_value = mock_repo
    mock_env_dir.return_value = 'dir_value'
    mock_env_branch.return_value = 'branch_value'

    with environ({}):
        os.environ.pop('DEPLOY_ENVIRONMENT', None)  # ensure not in env
        assert get_env('/', prompt_if_unexpected=True) == 'branch_value'
        mock_env_branch.assert_called_once_with('git_branch', True)

        # cases resulting in get_env_from_directory
        assert get_env('path', ignore_git_branch=True) == 'dir_value'
        mock_git_repo.side_effect = InvalidGitRepositoryError
        assert get_env('path') == 'dir_value'
        mock_env_dir.assert_has_calls([call('path'),
                                       call('path')])

        # handle TypeError
        mock_git_repo.side_effect = TypeError
        with pytest.raises(SystemExit):
            assert not get_env('path')
        mock_git_repo.side_effect = None

    with environ({'DEPLOY_ENVIRONMENT': 'test'}):
        assert get_env('path') == 'test'


@patch('runway.commands.runway_command.get_env_from_user')
def test_get_env_from_branch(mock_user):
    """Test runway.commands.runway_command.get_env_from_branch."""
    mock_user.return_value = 'user_value'

    assert get_env_from_branch('ENV-dev', prompt_if_unexpected=True) == 'dev'

    assert get_env_from_branch('master', prompt_if_unexpected=True) == 'common'

    assert get_env_from_branch('invalid', prompt_if_unexpected=True) == 'user_value'


def test_get_env_from_directory():
    """Test runway.commands.runway_command.get_env_from_directory."""
    assert get_env_from_directory('ENV-dev') == 'dev'
    assert get_env_from_directory('expected') == 'expected'


def test_get_env_from_user():
    """Test runway.commands.runway_command.get_env_from_user."""
    input_path = 'runway.commands.runway_command.input'

    with patch(input_path, MagicMock(return_value='n')):
        assert get_env_from_user('expected') == 'expected'

    with patch(input_path, MagicMock(side_effect=['y', '', 'expected'])):
        assert get_env_from_user('test') == 'expected'
