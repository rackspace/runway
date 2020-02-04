"""Runway base module."""
from __future__ import print_function

import logging
import os
import sys

from .base_command import BaseCommand
from .. import __version__ as version

LOGGER = logging.getLogger('runway')


class RunwayCommand(BaseCommand):
    """Base class for deployer classes."""

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

    @staticmethod
    def version():
        """Show current package version."""
        print(version)

    def execute(self):
        # type: () -> None
        """Execute the command."""
        raise NotImplementedError('execute must be implimented for '
                                  'subclasses of BaseCommand.')


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
                    '("ignore_git_branch" is set to true in the Runway '
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
        except TypeError:
            LOGGER.warning('Unable to retrieve the current git branch name!')
            LOGGER.warning('Typically this occurs when operating in a '
                           'detached-head state (e.g. what Jenkins uses when '
                           'checking out a git branch). Set the '
                           'DEPLOY_ENVIRONMENT environment variable to the '
                           'name of the logical environment (e.g. "export '
                           'DEPLOY_ENVIRONMENT=dev") to bypass this error.')
            sys.exit(1)
    LOGGER.info('Deriving environment name from directory %s...', path)
    return get_env_from_directory(os.path.basename(path))
