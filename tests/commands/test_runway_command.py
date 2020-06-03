"""Test runway.commands.runway_command."""
# pylint: disable=no-self-use
import os

import pytest
from git import InvalidGitRepositoryError
from mock import MagicMock, call, patch
from runway import __version__
from runway.commands.runway_command import (RunwayCommand, get_env,
                                            get_env_from_branch,
                                            get_env_from_directory,
                                            get_env_from_user)
from runway.util import environ

MODULE = 'runway.commands.runway_command'
PATCH_RUNWAY_CONFIG = 'runway.commands.base_command.Config'


@pytest.mark.usefixtures('patch_runway_config')
class TestRunwayCommand(object):
    """Test runway.commands.runway_command.RunwayCommand."""

    def test_execute(self):
        """Test execute."""
        with pytest.raises(NotImplementedError) as excinfo:
            assert RunwayCommand().execute()
        assert str(excinfo.value) == \
            'execute must be implimented for subclasses of BaseCommand.'

    def test_get_empty_dirs(self, tmp_path):
        """Test get_empty_dirs."""
        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == []

        dir_1 = tmp_path / 'dir_1'
        dir_1.mkdir()
        dir_2 = tmp_path / 'dir_2'
        dir_2.mkdir()

        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == ['dir_2',
                                                               'dir_1']

        (tmp_path / 'test_file').touch()
        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == ['dir_2',
                                                               'dir_1']

        (tmp_path / '.git').mkdir()  # skip even if it is empty
        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == ['dir_2',
                                                               'dir_1']

        (dir_2 / 'test_file').touch()
        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == ['dir_1']

        (dir_1 / 'test_file').touch()
        assert RunwayCommand.get_empty_dirs(str(tmp_path)) == []

    def test_path_only_contains_dirs(self, tmp_path):
        """Test path_only_contains_dirs."""
        assert RunwayCommand.path_only_contains_dirs(str(tmp_path)) is True

        (tmp_path / 'test_file').touch()
        assert RunwayCommand.path_only_contains_dirs(str(tmp_path)) is False
        (tmp_path / 'test_file').unlink()

        dir_1 = tmp_path / 'dir_1'
        dir_1.mkdir()
        dir_2 = tmp_path / 'dir_2'
        dir_2.mkdir()
        assert RunwayCommand.path_only_contains_dirs(str(tmp_path)) is True

        (dir_1 / 'test_file').touch()
        assert RunwayCommand.path_only_contains_dirs(str(tmp_path)) is False

    def test_version(self, capsys):
        """Test version."""
        assert not RunwayCommand.version()
        assert capsys.readouterr().out == (__version__ + '\n')


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


@pytest.mark.parametrize('branch, do_prompt, did_prompt, expected', [
    ('ENV-dev', True, False, 'dev'),
    ('master', True, False, 'common'),
    ('invalid', True, True, 'user_value'),
    ('invalid', False, False, 'invalid')
])
def test_get_env_from_branch(branch, do_prompt, did_prompt, expected, monkeypatch):
    """Test runway.commands.runway_command.get_env_from_branch."""
    mock_prompt = MagicMock(return_value='user_value')
    monkeypatch.setattr('runway.commands.runway_command.get_env_from_user',
                        mock_prompt)
    assert get_env_from_branch(branch, do_prompt) == expected

    if did_prompt:
        mock_prompt.assert_called_once_with(branch)
    else:
        mock_prompt.assert_not_called()


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
