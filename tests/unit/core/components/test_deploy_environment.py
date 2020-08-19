"""Test runway.core.components.deploy_environment."""
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

MODULE = "runway.core.components._deploy_environment"

TEST_CREDENTIALS = {
    "AWS_ACCESS_KEY_ID": "foo",
    "AWS_SECRET_ACCESS_KEY": "bar",
    "AWS_SESSION_TOKEN": "foobar",
}


class TestDeployEnvironment(object):
    """Test runway.core.components.DeployEnvironment."""

    def test_init(self, cd_tmp_path):
        """Test attributes set by init."""
        new_dir = cd_tmp_path / "new_dir"
        obj = DeployEnvironment(
            environ={"key": "val"},
            explicit_name="test",
            ignore_git_branch=True,
            root_dir=new_dir,
        )

        assert obj._ignore_git_branch
        assert obj.root_dir == new_dir
        assert obj.vars == {"key": "val"}

    def test_init_defaults(self, cd_tmp_path):
        """Test attributes set by init default values."""
        obj = DeployEnvironment()

        assert not obj._ignore_git_branch
        assert obj.name_derived_from is None
        assert obj.root_dir == cd_tmp_path
        assert obj.vars == os.environ

    def test_boto3_credentials(self):
        """Test boto3_credentials."""
        obj = DeployEnvironment(environ=TEST_CREDENTIALS)
        assert obj.aws_credentials == TEST_CREDENTIALS

    def test_aws_profile(self):
        """Test aws_profile."""
        env_vars = {"key": "val"}
        profile_name = "something"
        obj = DeployEnvironment(environ=env_vars)

        assert not obj.aws_profile

        obj.aws_profile = profile_name
        assert obj.aws_profile == profile_name
        assert obj.vars["AWS_PROFILE"] == profile_name

    def test_aws_region(self):
        """Test aws_region."""
        env_vars = {"AWS_REGION": "us-east-1", "AWS_DEFAULT_REGION": "us-west-2"}
        obj = DeployEnvironment(environ=env_vars)

        assert obj.aws_region == "us-east-1"

        del obj.vars["AWS_REGION"]
        assert obj.aws_region == "us-west-2"

        del obj.vars["AWS_DEFAULT_REGION"]
        assert not obj.aws_region

        obj.aws_region = "us-east-1"
        assert obj.aws_region == "us-east-1"
        assert obj.vars["AWS_REGION"] == "us-east-1"
        assert obj.vars["AWS_DEFAULT_REGION"] == "us-east-1"

    @patch(MODULE + ".git")
    def test_branch_name(self, mock_git):
        """Test branch_name."""
        branch_name = "test"
        mock_repo = MagicMock()
        mock_repo.active_branch.name = branch_name
        mock_git.Repo.return_value = mock_repo

        obj = DeployEnvironment()
        assert obj.branch_name == branch_name
        mock_git.Repo.assert_called_once_with(
            os.getcwd(), search_parent_directories=True
        )

    @patch(MODULE + ".git")
    def test_branch_name_invalid_repo(self, mock_git):
        """Test branch_name handle InvalidGitRepositoryError."""
        mock_git.Repo.side_effect = InvalidGitRepositoryError

        obj = DeployEnvironment()
        assert obj.branch_name is None
        mock_git.Repo.assert_called_once_with(
            os.getcwd(), search_parent_directories=True
        )

    def test_branch_name_no_git(self, monkeypatch, caplog):
        """Test branch_name git ImportError."""
        caplog.set_level(logging.DEBUG, logger="runway.core.components")
        monkeypatch.setattr(MODULE + ".git", object)
        obj = DeployEnvironment()

        assert obj.branch_name is None
        assert (
            "failed to import git; ensure git is your path and executable "
            "to read the branch name"
        ) in caplog.messages

    @patch(MODULE + ".git")
    def test_branch_name_type_error(self, mock_git, caplog):
        """Test branch_name handle TypeError."""
        caplog.set_level(logging.WARNING, logger="runway")
        mock_git.Repo.side_effect = TypeError

        with pytest.raises(SystemExit) as excinfo:
            obj = DeployEnvironment()
            assert not obj.branch_name

        assert excinfo.value.code == 1
        assert "Unable to retrieve the current git branch name!" in caplog.messages

    def test_ci(self):
        """Test ci."""
        obj = DeployEnvironment(environ={})

        assert not obj.ci

        obj.ci = True
        assert obj.ci
        assert obj.vars["CI"] == "1"

        obj.ci = False
        assert not obj.ci
        assert "CI" not in obj.vars

    def test_debug(self):
        """Test debug."""
        obj = DeployEnvironment(environ={})

        assert not obj.debug

        obj.debug = True
        assert obj.debug
        assert obj.vars["DEBUG"] == "1"

        obj.debug = False
        assert not obj.debug
        assert "DEBUG" not in obj.vars

    def test_ignore_git_branch(self):
        """Test ignore_git_branch."""
        obj = DeployEnvironment(environ={}, explicit_name="first")

        assert not obj.ignore_git_branch
        assert obj.name == "first"

        obj._DeployEnvironment__name = "second"
        obj.ignore_git_branch = False
        assert obj.name == "first"
        assert not obj.ignore_git_branch

        obj.ignore_git_branch = True
        assert obj.name == "second"
        assert obj.ignore_git_branch

        # delete attr before setting new val to force AttributeError
        del obj.name
        obj.ignore_git_branch = False
        assert obj.name == "second"

    def test_max_concurrent_cfngin_stacks(self):
        """Test max_concurrent_cfngin_stacks."""
        obj = DeployEnvironment(environ={})

        assert obj.max_concurrent_cfngin_stacks == 0

        obj.max_concurrent_cfngin_stacks = 5
        assert obj.max_concurrent_cfngin_stacks == 5
        assert obj.vars["RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS"] == 5

    @patch(MODULE + ".multiprocessing")
    def test_max_concurrent_modules(self, mock_proc):
        """Test max_concurrent_modules."""
        mock_proc.cpu_count.return_value = 4
        obj = DeployEnvironment(environ={})

        assert obj.max_concurrent_modules == 4

        mock_proc.cpu_count.return_value = 62
        assert obj.max_concurrent_modules == 61

        obj.max_concurrent_modules = 12
        assert obj.max_concurrent_modules == 12
        assert obj.vars["RUNWAY_MAX_CONCURRENT_MODULES"] == 12

    @patch(MODULE + ".multiprocessing")
    def test_max_concurrent_regions(self, mock_proc):
        """Test max_concurrent_regions."""
        mock_proc.cpu_count.return_value = 4
        obj = DeployEnvironment(environ={})

        assert obj.max_concurrent_regions == 4

        mock_proc.cpu_count.return_value = 62
        assert obj.max_concurrent_regions == 61

        obj.max_concurrent_regions = 12
        assert obj.max_concurrent_regions == 12
        assert obj.vars["RUNWAY_MAX_CONCURRENT_REGIONS"] == 12

    def test_name(self):
        """Test name."""
        obj = DeployEnvironment(explicit_name="test")
        assert obj.name == "test"
        assert obj.name_derived_from == "explicit"

        obj.name = "test2"
        assert obj.name == "test2"

        del obj.name
        obj.name = "test3"
        assert obj.name == "test3"

    @pytest.mark.parametrize(
        "branch, environ, expected",
        [
            ("ENV-dev", {}, "dev"),
            ("master", {}, "common"),
            ("invalid", {}, "user_value"),
            ("invalid", {"CI": "1"}, "invalid"),
        ],
    )
    def test_name_from_branch(self, branch, environ, expected, monkeypatch):
        """Test name from branch."""
        mock_prompt = MagicMock(return_value="user_value")
        monkeypatch.setattr(MODULE + ".click.prompt", mock_prompt)
        monkeypatch.setattr(DeployEnvironment, "branch_name", branch)
        obj = DeployEnvironment(environ=environ)
        assert obj.name == expected
        if expected == "user_value":
            assert obj.name_derived_from == "explicit"
        else:
            assert obj.name_derived_from == "branch"

        if obj.ci:
            mock_prompt.assert_not_called()

    @pytest.mark.parametrize(
        "root_dir, expected",
        [(Path.cwd() / "ENV-dev", "dev"), (Path.cwd() / "common", "common")],
    )
    def test_name_from_directory(self, root_dir, expected, monkeypatch):
        """Test name from directory."""
        monkeypatch.setattr(DeployEnvironment, "branch_name", None)
        obj = DeployEnvironment(ignore_git_branch=True, root_dir=root_dir)
        assert obj.name == expected
        assert obj.name_derived_from == "directory"

    def test_verbose(self):
        """Test verbose."""
        obj = DeployEnvironment(environ={})

        assert not obj.verbose

        obj.verbose = True
        assert obj.verbose
        assert obj.vars["VERBOSE"] == "1"

        obj.verbose = False
        assert not obj.verbose
        assert "VERBOSE" not in obj.vars

    def test_copy(self, monkeypatch, tmp_path):
        """Test copy."""
        monkeypatch.setattr(DeployEnvironment, "name", "test")
        obj = DeployEnvironment(root_dir=tmp_path)
        obj_copy = obj.copy()

        assert obj_copy != obj
        assert obj_copy._ignore_git_branch == obj._ignore_git_branch
        assert obj_copy.name == obj.name
        assert obj_copy.name_derived_from == obj.name_derived_from
        assert obj_copy.root_dir == obj.root_dir
        assert obj_copy.vars == obj.vars

    @pytest.mark.parametrize(
        "derived_from, expected",
        [
            (
                "explicit",
                [
                    'deploy environment "test" is explicitly defined '
                    "in the environment",
                    "if not correct, update the value or unset it to "
                    "fall back to the name of the current git branch "
                    "or parent directory",
                ],
            ),
            (
                "branch",
                [
                    'deploy environment "test" was determined from the '
                    "current git branch",
                    "if not correct, update the branch name or set an "
                    "override via the DEPLOY_ENVIRONMENT environment "
                    "variable",
                ],
            ),
            (
                "directory",
                [
                    'deploy environment "test" was determined from '
                    "the current directory",
                    "if not correct, update the directory name or "
                    "set an override via the DEPLOY_ENVIRONMENT "
                    "environment variable",
                ],
            ),
        ],
    )
    def test_log_name(self, derived_from, expected, caplog, monkeypatch):
        """Test log_name."""
        caplog.set_level(logging.INFO, logger="runway")
        monkeypatch.setattr(DeployEnvironment, "name", "test")
        obj = DeployEnvironment()
        obj.name_derived_from = derived_from
        obj.log_name()
        assert caplog.messages == expected
