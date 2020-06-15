"""Core Runway components."""
import logging
import os
import sys
from typing import Any, Dict, Optional  # pylint: disable=W

import click

from ..util import cached_property

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

try:  # will raise an import error if git is not in the current path
    import git
    from git.exc import InvalidGitRepositoryError
except ImportError:  # cov: ignore
    git = object  # pylint: disable=invalid-name
    InvalidGitRepositoryError = AttributeError

LOGGER = logging.getLogger(__name__)


class DeployEnvironment(object):
    """Runway deploy environment."""

    def __init__(self,
                 *_,  # type: Any
                 environ=None,  # type: Optional[Dict[str, str]]
                 explicit_name=None,  # type: Optional[str]
                 ignore_git_branch=False,  # type: bool
                 root_dir=None  # type: Optional[Path]
                 ):
        # type: (...) -> None
        """Instantiate class.

        Keyword Args:
            environ (Optional[Dict[str, str]]): Environment variables.
            explicit_name (Optional[str]): Explicitly provide the deploy
                environment name.
            ignore_git_branch (bool): Ignore the git branch when determining
                the deploy environment name.
            root_dir (Optional[Path]): Root directory of the project.

        """
        self.__name = explicit_name
        self._ignore_git_branch = ignore_git_branch
        self.name_derived_from = 'explicit' if explicit_name else None
        self.root_dir = root_dir if root_dir else Path.cwd()
        self.vars = environ or os.environ.copy()

    @cached_property
    def branch_name(self):
        # type: () -> Optional[str]
        """Git branch name."""
        if isinstance(git, type):
            LOGGER.debug('failed to import git; ensure git is your path and '
                         'executable to read the branch name')
            return None
        try:
            LOGGER.debug('getting git branch name...')
            return git.Repo(str(self.root_dir),
                            search_parent_directories=True).active_branch.name
        except TypeError:
            LOGGER.warning('Unable to retrieve the current git branch name!')
            LOGGER.warning('Typically this occurs when operating in a '
                           'detached-head state (e.g. what Jenkins uses when '
                           'checking out a git branch). Set the '
                           'DEPLOY_ENVIRONMENT environment variable to the '
                           'name of the logical environment (e.g. "export '
                           'DEPLOY_ENVIRONMENT=dev") to bypass this error.')
            sys.exit(1)
        except InvalidGitRepositoryError:
            return None

    @property
    def ci(self):
        """Return CI status.

        Returns:
            bool

        """
        return 'CI' in self.vars

    @ci.setter
    def ci(self, value):
        """Set the value of CI."""
        if value:
            self.vars['CI'] = '1'
        else:
            self.vars.pop('CI', None)

    @cached_property
    def name(self):
        # type: () -> str
        """Deploy environment name."""
        if self.__name:
            return self.__name
        if not self._ignore_git_branch and self.branch_name:
            self.name_derived_from = 'branch'
            return self._parse_branch_name()
        self.name_derived_from = 'directory'
        return self.root_dir.name[4:] \
            if self.root_dir.name.startswith('ENV-') else self.root_dir.name

    def _parse_branch_name(self):
        # type: () -> str
        """Parse branch name for use as deploy environment name."""
        if self.branch_name.startswith('ENV-'):
            return self.branch_name[4:]
        if self.branch_name == 'master':
            LOGGER.info('Translating git branch "master" to environment '
                        '"common"')
            return 'common'
        if not self.ci:
            LOGGER.warning('Found unexpected branch name "%s"',
                           self.branch_name)
            return click.prompt('Deploy environment name',
                                default=self.branch_name, type=click.STRING)
        return self.branch_name
