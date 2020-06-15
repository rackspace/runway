"""Test runway.core.components."""
# pylint: disable=no-self-use,protected-access
import logging
import os
import sys

import pytest
from git.exc import InvalidGitRepositoryError
from mock import MagicMock, patch

from runway.core.components import DeployEnvironment

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

MODULE = 'runway.core.components'


class TestDeployEnvironment(object):
    """Test runway.core.components.DeployEnvironment."""

    @patch(MODULE + '.git')
    def test_branch_name(self, mock_git):
        """Test branch_name."""
        branch_name = 'test'
        mock_repo = MagicMock()
        mock_repo.active_branch.name = branch_name
        mock_git.Repo.return_value = mock_repo

        obj = DeployEnvironment()
        assert obj.branch_name == branch_name
        mock_git.Repo.assert_called_once_with(os.getcwd(),
                                              search_parent_directories=True)

    @patch(MODULE + '.git')
    def test_branch_name_invalid_repo(self, mock_git):
        """Test branch_name handle InvalidGitRepositoryError."""
        mock_git.Repo.side_effect = InvalidGitRepositoryError

        obj = DeployEnvironment()
        assert obj.branch_name is None
        mock_git.Repo.assert_called_once_with(os.getcwd(),
                                              search_parent_directories=True)

    def test_branch_name_no_git(self, monkeypatch, caplog):
        """Test branch_name git ImportError."""
        caplog.set_level(logging.DEBUG, logger='runway.core.components')
        monkeypatch.setattr(MODULE + '.git', object)
        obj = DeployEnvironment()

        assert obj.branch_name is None
        assert ('failed to import git; ensure git is your path and executable '
                'to read the branch name') in caplog.messages

    @patch(MODULE + '.git')
    def test_branch_name_type_error(self, mock_git, caplog):
        """Test branch_name handle TypeError."""
        caplog.set_level(logging.WARNING, logger='runway')
        mock_git.Repo.side_effect = TypeError

        with pytest.raises(SystemExit) as excinfo:
            obj = DeployEnvironment()
            assert not obj.branch_name

        assert excinfo.value.code == 1
        assert 'Unable to retrieve the current git branch name!' in \
            caplog.messages

    def test_ci(self):
        """Test ci."""
        obj = DeployEnvironment(environ={})

        assert not obj.ci

        obj.ci = True
        assert obj.ci
        assert obj.vars['CI'] == '1'

        obj.ci = None
        assert not obj.ci
        assert 'CI' not in obj.vars

    def test_init(self, cd_tmp_path):
        """Test attributes set by init."""
        new_dir = cd_tmp_path / 'new_dir'
        obj = DeployEnvironment(environ={'key': 'val'},
                                explicit_name='test',
                                ignore_git_branch=True,
                                root_dir=new_dir)

        assert obj._ignore_git_branch
        assert obj.root_dir == new_dir
        assert obj.vars == {'key': 'val'}

    def test_init_defaults(self, cd_tmp_path):
        """Test attributes set by init default values."""
        obj = DeployEnvironment()

        assert not obj._ignore_git_branch
        assert obj.name_derived_from is None
        assert obj.root_dir == cd_tmp_path
        assert obj.vars == os.environ

    def test_name(self):
        """Test name."""
        obj = DeployEnvironment(explicit_name='test')
        assert obj.name == 'test'
        assert obj.name_derived_from == 'explicit'

    @pytest.mark.parametrize('branch, environ, expected', [
        ('ENV-dev', {}, 'dev'),
        ('master', {}, 'common'),
        ('invalid', {}, 'user_value'),
        ('invalid', {'CI': '1'}, 'invalid')
    ])
    def test_name_from_branch(self, branch, environ, expected, monkeypatch):
        """Test name from branch."""
        mock_prompt = MagicMock(return_value='user_value')
        monkeypatch.setattr('runway.core.components.click.prompt',
                            mock_prompt)
        monkeypatch.setattr(DeployEnvironment, 'branch_name', branch)
        obj = DeployEnvironment(environ=environ)
        assert obj.name == expected
        assert obj.name_derived_from == 'branch'

        if obj.ci:
            mock_prompt.assert_not_called()

    @pytest.mark.parametrize('root_dir, expected', [
        (Path.cwd() / 'ENV-dev', 'dev'),
        (Path.cwd() / 'common', 'common')
    ])
    def test_name_from_directory(self, root_dir, expected, monkeypatch):
        """Test name from directory."""
        monkeypatch.setattr(DeployEnvironment, 'branch_name', None)
        obj = DeployEnvironment(ignore_git_branch=True, root_dir=root_dir)
        assert obj.name == expected
        assert obj.name_derived_from == 'directory'
