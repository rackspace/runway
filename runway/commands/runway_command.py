"""runway base module."""
from __future__ import print_function

import glob
import logging
import os
import sys

import yaml

from .. import __version__ as version

LOGGER = logging.getLogger('runway')


class RunwayCommand(object):
    """Base class for deployer classes."""

    def __init__(self, cli_arguments, env_root=None, runway_config_dir=None):
        """Initialize base class."""
        self._cli_arguments = cli_arguments

        if env_root is None:
            self.env_root = os.getcwd()
        else:
            self.env_root = env_root

        if runway_config_dir is None:
            self.runway_config_path = os.path.join(
                self.env_root,
                'runway.yml'
            )
        else:
            self.runway_config_path = os.path.join(
                runway_config_dir,
                'runway.yml'
            )
        self._runway_config = None

    def get_env_dirs(self):
        """Return list of directories in env_root."""
        repo_dirs = next(os.walk(self.env_root))[1]
        if '.git' in repo_dirs:
            repo_dirs.remove('.git')  # not relevant for any repo operations
        return repo_dirs

    def get_python_files_at_env_root(self):
        """Return list of python files in env_root."""
        return glob.glob(os.path.join(self.env_root, '*.py'))

    def get_yaml_files_at_env_root(self):
        """Return list of yaml files in env_root."""
        yaml_files = glob.glob(
            os.path.join(self.env_root, '*.yaml')
        )
        yml_files = glob.glob(
            os.path.join(self.env_root, '*.yml')
        )
        return yaml_files + yml_files

    def get_cookbook_dirs(self, base_dir=None):
        """Find cookbook directories."""
        if base_dir is None:
            base_dir = self.env_root

        cookbook_dirs = []
        dirs_to_skip = set(['.git'])
        for root, dirs, files in os.walk(base_dir):  # pylint: disable=W0612
            dirs[:] = [d for d in dirs if d not in dirs_to_skip]
            for name in files:
                if name == 'metadata.rb':
                    if 'cookbook' in os.path.basename(os.path.dirname(root)):
                        cookbook_dirs.append(root)
        return cookbook_dirs

    def path_only_contains_dirs(self, path):
        """Return boolean on whether a path only contains directories."""
        pathlistdir = os.listdir(path)
        if pathlistdir == []:
            return True
        if any(os.path.isfile(os.path.join(path, i)) for i in pathlistdir):
            return False
        return all(self.path_only_contains_dirs(os.path.join(path, i)) for i in pathlistdir)  # noqa

    def get_empty_dirs(self, path):
        """Return a list of empty directories in path."""
        empty_dirs = []
        for i in os.listdir(path):
            child_path = os.path.join(path, i)
            if i == '.git' or os.path.isfile(child_path) or os.path.islink(child_path):  # noqa
                continue
            if self.path_only_contains_dirs(child_path):
                empty_dirs.append(i)
        return empty_dirs

    def parse_runway_config(self):
        """Read and parse runway.yml."""
        if not os.path.isfile(self.runway_config_path):
            LOGGER.error("Runway config file was not found (looking for "
                         "%s)",
                         self.runway_config_path)
            sys.exit(1)
        with open(self.runway_config_path) as data_file:
            return yaml.safe_load(data_file)

    @property
    def runway_config(self):
        """Return parsed runway.yml."""
        if not self._runway_config:
            self._runway_config = self.parse_runway_config()
        return self._runway_config

    @staticmethod
    def version():
        """Show current package version."""
        print(version)


def get_env_from_branch(branch_name):
    """Determine environment name from git branch name."""
    if branch_name.startswith('ENV-'):
        return branch_name[4:]
    if branch_name == 'master':
        LOGGER.info('Translating git branch "master" to environment '
                    '"common"')
        return 'common'
    return branch_name


def get_env_from_directory(directory_name):
    """Determine environment name from directory name."""
    if directory_name.startswith('ENV-'):
        return directory_name[4:]
    return directory_name


def get_env(path, ignore_git_branch=False):
    """Determine environment name."""
    if 'DEPLOY_ENVIRONMENT' in os.environ:
        return os.environ['DEPLOY_ENVIRONMENT']

    if ignore_git_branch:
        LOGGER.info('Skipping environment lookup from current git branch '
                    '("ignore_git_branch" is set to true in the runway '
                    'config)')
    else:
        # These are not located with the top imports because they throw an
        # error if git isn't installed
        from git import Repo as GitRepo
        from git.exc import InvalidGitRepositoryError

        try:
            b_name = GitRepo(
                path,
                search_parent_directories=True
            ).active_branch.name
            LOGGER.info('Deriving environment name from git branch %s...',
                        b_name)
            return get_env_from_branch(b_name)
        except InvalidGitRepositoryError:
            pass
    LOGGER.info('Deriving environment name from directory %s...', path)
    return get_env_from_directory(os.path.basename(path))
