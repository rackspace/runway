"""Runway deploy environment object."""
import logging
# needed for python2 cpu_count, can be replace with python3 os.cpu_count()
import multiprocessing
import os
import sys
from typing import Any, Dict, Optional, Union  # pylint: disable=W

import click

from ...util import AWS_ENV_VARS, cached_property

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

LOGGER = logging.getLogger(__name__.replace('._', '.'))


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

    @property
    def aws_credentials(self):
        # type: () -> Dict[str, str]
        """Get AWS credentials from environment variables."""
        return {name: self.vars.get(name)
                for name in AWS_ENV_VARS if self.vars.get(name)}

    @property
    def aws_profile(self):
        # type: () -> Optional[str]
        """Get AWS profile from environment variables."""
        return self.vars.get('AWS_PROFILE')

    @aws_profile.setter
    def aws_profile(self, profile_name):
        # type: (str) -> None
        """Set AWS profile in the environment."""
        self.vars['AWS_PROFILE'] = profile_name

    @property
    def aws_region(self):
        # type: () -> Optional[str]
        """Get AWS region from environment variables."""
        return self.vars.get('AWS_REGION', self.vars.get('AWS_DEFAULT_REGION'))

    @aws_region.setter
    def aws_region(self, region):
        # type: (str) -> None
        """Set AWS region environment variables."""
        self.vars.update({'AWS_DEFAULT_REGION': region, 'AWS_REGION': region})

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
        # type: () -> bool
        """Return CI status.

        Returns:
            bool

        """
        return 'CI' in self.vars

    @ci.setter
    def ci(self, value):
        # type: (Any) -> None
        """Set the value of CI."""
        if value:
            self.vars['CI'] = '1'
        else:
            self.vars.pop('CI', None)

    @property
    def debug(self):
        # type: () -> bool
        """Get debug setting from the environment."""
        return 'DEBUG' in self.vars

    @debug.setter
    def debug(self, value):
        # type: (Any) -> None
        """Set the value of DEBUG."""
        if value:
            self.vars['DEBUG'] = '1'
        else:
            self.vars.pop('DEBUG', None)

    @property
    def max_concurrent_cfngin_stacks(self):
        # type: () -> int
        """Max number of CFNgin stacks that can be deployed concurrently.

        This property can be set by exporting
        ``RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS``. If no value is specified, the
        value will be constrained based on the underlying graph.

        Returns:
            int: Value from environment variable or ``0``.

        """
        return int(
            self.vars.get('RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS', '0')
        )

    @max_concurrent_cfngin_stacks.setter
    def max_concurrent_cfngin_stacks(self, value):
        # type: (Union[int, str]) -> None
        """Set RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS."""
        self.vars['RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS'] = value

    @property
    def max_concurrent_modules(self):
        # type: () -> int
        """Max number of modules that can be deployed to concurrently.

        This property can be set by exporting ``RUNWAY_MAX_CONCURRENT_MODULES``.
        If no value is specified, ``min(61, os.cpu_count())`` is used.

        On Windows, this must be equal to or lower than ``61``.

        **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
        together, please consider the nature of their relationship when
        manually setting this value. (``parallel_regions * child_modules``)

        Returns:
            int: Value from environment variable or ``min(61, os.cpu_count())``

        """
        value = self.vars.get('RUNWAY_MAX_CONCURRENT_MODULES')

        if value:
            return int(value)
        # TODO update to `os.cpu_count()` when dropping python2
        return min(61, multiprocessing.cpu_count())

    @max_concurrent_modules.setter
    def max_concurrent_modules(self, value):
        # type: (Union[int, str])-> None
        """Set RUNWAY_MAX_CONCURRENT_MODULES."""
        self.vars['RUNWAY_MAX_CONCURRENT_MODULES'] = value

    @property
    def max_concurrent_regions(self):
        # type: () -> int
        """Max number of regions that can be deployed to concurrently.

        This property can be set by exporting ``RUNWAY_MAX_CONCURRENT_REGIONS``.
        If no value is specified, ``min(61, os.cpu_count())`` is used.

        On Windows, this must be equal to or lower than ``61``.

        **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
        together, please consider the nature of their relationship when
        manually setting this value. (``parallel_regions * child_modules``)

        Returns:
            int: Value from environment variable or ``min(61, os.cpu_count())``

        """
        value = self.vars.get('RUNWAY_MAX_CONCURRENT_REGIONS')

        if value:
            return int(value)
        # TODO update to `os.cpu_count()` when dropping python2
        return min(61, multiprocessing.cpu_count())

    @max_concurrent_regions.setter
    def max_concurrent_regions(self, value):
        # type: (Union[int, str]) -> None
        """Set RUNWAY_MAX_CONCURRENT_REGIONS."""
        self.vars['RUNWAY_MAX_CONCURRENT_REGIONS'] = value

    @cached_property
    def name(self):
        # type: () -> str
        """Deploy environment name."""
        if self.__name:
            name = self.__name
        elif not self._ignore_git_branch and self.branch_name:
            self.name_derived_from = self.name_derived_from or 'branch'
            name = self._parse_branch_name()
        else:
            self.name_derived_from = 'directory'
            name = self.root_dir.name[4:] \
                if self.root_dir.name.startswith('ENV-') else self.root_dir.name
        self.vars['DEPLOY_ENVIRONMENT'] = name
        return name

    def copy(self):
        # type: () -> DeployEnvironment
        """Copy the contents of this object into a new instance.

        Returns:
            DeployEnvironment: New instance with the same contents.

        """
        obj = self.__class__(environ=self.vars.copy(),
                             explicit_name=self.name,
                             ignore_git_branch=self._ignore_git_branch,
                             root_dir=self.root_dir)
        obj.name_derived_from = self.name_derived_from
        return obj

    def log_name(self):
        # type: () -> None
        """Output name to log."""
        name = self.name  # resolve if not already resolved
        LOGGER.info('')
        if self.name_derived_from == 'explicit':
            LOGGER.info('Environment "%s" is explicitly defined in the environment.',
                        name)
            LOGGER.info('If this is not correct, update '
                        'the value or unset it to fall back to the name of '
                        'the current git branch or parent directory.')
        elif self.name_derived_from == 'branch':
            LOGGER.info('Environment "%s" was determined from the current git branch.',
                        name)
            LOGGER.info('If this is not the environment name, update the '
                        'branch name or set an override via the '
                        'DEPLOY_ENVIRONMENT environment variable.')
        elif self.name_derived_from == 'directory':
            LOGGER.info('Environment "%s" was determined from the current directory.',
                        name)
            LOGGER.info('If this is not the environment name, update the '
                        'directory name or set an override via the '
                        'DEPLOY_ENVIRONMENT environment variable.')
        LOGGER.info('')

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
            result = click.prompt('Deploy environment name',
                                  default=self.branch_name, type=click.STRING)
            if result != self.branch_name:
                self.name_derived_from = 'explicit'
            return result
        return self.branch_name
