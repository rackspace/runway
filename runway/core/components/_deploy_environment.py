"""Runway deploy environment object."""
import json
import logging
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

LOGGER = logging.getLogger(__name__.replace("._", "."))


class DeployEnvironment(object):
    """Runway deploy environment."""

    # TODO implement propper keyword-only args when dropping python 2
    # def __init__(self,
    #              *: Any,
    #              environ: Optional[Dict[str, str]] = None,
    #              explicit_name: Optional[str] = None,
    #              ignore_git_branch: bool = False,
    #              root_dir: Optional[Path] = None
    #              ) -> None:
    def __init__(self, _=None, **kwargs):
        """Instantiate class.

        Keyword Args:
            environ (Optional[Dict[str, str]]): Environment variables.
            explicit_name (Optional[str]): Explicitly provide the deploy
                environment name.
            ignore_git_branch (bool): Ignore the git branch when determining
                the deploy environment name.
            root_dir (Optional[Path]): Root directory of the project.

        """
        self.__name = kwargs.pop("explicit_name", None)
        self._ignore_git_branch = kwargs.pop("ignore_git_branch", False)
        self.name_derived_from = "explicit" if self.__name else None
        root_dir = kwargs.pop("root_dir", None)
        self.root_dir = root_dir if root_dir else Path.cwd()
        self.vars = kwargs.pop("environ", os.environ.copy())

    @property
    def aws_credentials(self):
        # type: () -> Dict[str, str]
        """Get AWS credentials from environment variables."""
        return {
            name: self.vars.get(name) for name in AWS_ENV_VARS if self.vars.get(name)
        }

    @property
    def aws_profile(self):
        # type: () -> Optional[str]
        """Get AWS profile from environment variables."""
        return self.vars.get("AWS_PROFILE")

    @aws_profile.setter
    def aws_profile(self, profile_name):
        # type: (str) -> None
        """Set AWS profile in the environment."""
        self._update_vars({"AWS_PROFILE": profile_name})

    @property
    def aws_region(self):
        # type: () -> Optional[str]
        """Get AWS region from environment variables."""
        return self.vars.get("AWS_REGION", self.vars.get("AWS_DEFAULT_REGION"))

    @aws_region.setter
    def aws_region(self, region):
        # type: (str) -> None
        """Set AWS region environment variables."""
        self._update_vars({"AWS_DEFAULT_REGION": region, "AWS_REGION": region})

    @cached_property
    def branch_name(self):
        # type: () -> Optional[str]
        """Git branch name."""
        if isinstance(git, type):
            LOGGER.debug(
                "failed to import git; ensure git is your path and "
                "executable to read the branch name"
            )
            return None
        try:
            LOGGER.debug("getting git branch name...")
            return git.Repo(
                str(self.root_dir), search_parent_directories=True
            ).active_branch.name
        except TypeError:
            LOGGER.warning("Unable to retrieve the current git branch name!")
            LOGGER.warning(
                "Typically this occurs when operating in a "
                "detached-head state (e.g. what Jenkins uses when "
                "checking out a git branch). Set the "
                "DEPLOY_ENVIRONMENT environment variable to the "
                'name of the logical environment (e.g. "export '
                'DEPLOY_ENVIRONMENT=dev") to bypass this error.'
            )
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
        return "CI" in self.vars

    @ci.setter
    def ci(self, value):
        # type: (Any) -> None
        """Set the value of CI."""
        if value:
            self._update_vars({"CI": "1"})
        else:
            self.vars.pop("CI", None)

    @property
    def debug(self):
        # type: () -> bool
        """Get debug setting from the environment."""
        return "DEBUG" in self.vars

    @debug.setter
    def debug(self, value):
        # type: (Any) -> None
        """Set the value of DEBUG."""
        if value:
            self._update_vars({"DEBUG": "1"})
        else:
            self.vars.pop("DEBUG", None)

    @property
    def ignore_git_branch(self):
        # type: () -> bool
        """Whether to ignore git branch when determining name."""
        return self._ignore_git_branch

    @ignore_git_branch.setter
    def ignore_git_branch(self, value):
        # type: (bool) -> None
        """Set the value of ignore_git_branch.

        Cached name is deleted when changing this value.

        """
        if self._ignore_git_branch != value:
            self._ignore_git_branch = value
            try:
                del self.name
                LOGGER.debug(
                    "value of ignore_git_branch has changed; "
                    "cleared cached name so it can be determined again"
                )
            except AttributeError:
                pass  # it's fine if it does not exist yes

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
        return int(self.vars.get("RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS", "0"))

    @max_concurrent_cfngin_stacks.setter
    def max_concurrent_cfngin_stacks(self, value):
        # type: (Union[int, str]) -> None
        """Set RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS."""
        self._update_vars({"RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS": value})

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
        value = self.vars.get("RUNWAY_MAX_CONCURRENT_MODULES")

        if value:
            return int(value)
        # TODO update to `os.cpu_count()` when dropping python2
        return min(61, multiprocessing.cpu_count())

    @max_concurrent_modules.setter
    def max_concurrent_modules(self, value):
        # type: (Union[int, str])-> None
        """Set RUNWAY_MAX_CONCURRENT_MODULES."""
        self._update_vars({"RUNWAY_MAX_CONCURRENT_MODULES": value})

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
        value = self.vars.get("RUNWAY_MAX_CONCURRENT_REGIONS")

        if value:
            return int(value)
        # TODO update to `os.cpu_count()` when dropping python2
        return min(61, multiprocessing.cpu_count())

    @max_concurrent_regions.setter
    def max_concurrent_regions(self, value):
        # type: (Union[int, str]) -> None
        """Set RUNWAY_MAX_CONCURRENT_REGIONS."""
        self._update_vars({"RUNWAY_MAX_CONCURRENT_REGIONS": value})

    @cached_property
    def name(self):
        # type: () -> str
        """Deploy environment name."""
        if self.__name:
            name = self.__name
        elif not self.ignore_git_branch and self.branch_name:
            self.name_derived_from = self.name_derived_from or "branch"
            name = self._parse_branch_name()
        else:
            self.name_derived_from = "directory"
            if self.root_dir.name.startswith("ENV-"):
                LOGGER.verbose(
                    'stripped "ENV-" from the directory name "%s"', self.root_dir.name
                )
                name = self.root_dir.name[4:]
            else:
                name = self.root_dir.name
        if self.vars.get("DEPLOY_ENVIRONMENT") != name:
            self._update_vars({"DEPLOY_ENVIRONMENT": name})
        return name

    @property
    def verbose(self):
        # type: () -> bool
        """Get verbose setting from the environment."""
        return "VERBOSE" in self.vars

    @verbose.setter
    def verbose(self, value):
        # type: (Any) -> None
        """Set the value of VERBOSE."""
        if value:
            self._update_vars({"VERBOSE": "1"})
        else:
            self.vars.pop("VERBOSE", None)

    def copy(self):
        # type: () -> DeployEnvironment
        """Copy the contents of this object into a new instance.

        Returns:
            DeployEnvironment: New instance with the same contents.

        """
        LOGGER.debug("creating a copy of the deploy environment...")
        obj = self.__class__(
            environ=self.vars.copy(),
            explicit_name=self.name,
            ignore_git_branch=self._ignore_git_branch,
            root_dir=self.root_dir,
        )
        obj.name_derived_from = self.name_derived_from
        return obj

    def log_name(self):
        # type: () -> None
        """Output name to log."""
        name = self.name  # resolve if not already resolved
        if self.name_derived_from == "explicit":
            LOGGER.info(
                'deploy environment "%s" is explicitly defined in the environment', name
            )
            LOGGER.info(
                "if not correct, update the value or unset it to fall back "
                "to the name of the current git branch or parent directory"
            )
        elif self.name_derived_from == "branch":
            LOGGER.info(
                'deploy environment "%s" was determined from the current git branch',
                name,
            )
            LOGGER.info(
                "if not correct, update the branch name or set an override "
                "via the DEPLOY_ENVIRONMENT environment variable"
            )
        elif self.name_derived_from == "directory":
            LOGGER.info(
                'deploy environment "%s" was determined from the current directory',
                name,
            )
            LOGGER.info(
                "if not correct, update the directory name or set an "
                "override via the DEPLOY_ENVIRONMENT environment variable"
            )

    def _parse_branch_name(self):
        # type: () -> str
        """Parse branch name for use as deploy environment name."""
        if self.branch_name.startswith("ENV-"):
            LOGGER.verbose(
                'stripped "ENV-" from the branch name "%s"', self.branch_name
            )
            return self.branch_name[4:]
        if self.branch_name == "master":
            LOGGER.verbose('translated branch name "master" to "common"')
            return "common"
        if not self.ci:
            LOGGER.warning('Found unexpected branch name "%s"', self.branch_name)
            result = click.prompt(
                "Deploy environment name", default=self.branch_name, type=click.STRING
            )
            if result != self.branch_name:
                self.name_derived_from = "explicit"
            return result
        return self.branch_name

    def _update_vars(self, env_vars):
        # type: (Dict[str, str]) -> None
        """Update vars and log the change.

        Args:
            env_vars (Dict[str, str]): Dict to update self.vars with.

        """
        self.vars.update(env_vars)
        LOGGER.verbose("updated environment variables: %s", json.dumps(env_vars))
