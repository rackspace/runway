"""Runway module module."""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from collections.abc import MutableMapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union, cast

from ..util import merge_nested_environment_dicts, which

if TYPE_CHECKING:
    from .._logging import PrefixAdaptor, RunwayLogger
    from ..context import Context

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))
NPM_BIN = "npm.cmd" if platform.system().lower() == "windows" else "npm"
NPX_BIN = "npx.cmd" if platform.system().lower() == "windows" else "npx"


def format_npm_command_for_logging(command: List[str]) -> str:
    """Convert npm command list to string for display to user."""
    if platform.system().lower() == "windows" and (
        command[0] == "npx.cmd" and command[1] == "-c"
    ):
        return 'npx.cmd -c "%s"' % " ".join(command[2:])
    return " ".join(command)


def generate_node_command(
    command: str,
    command_opts: List[str],
    path: Path,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> List[str]:
    """Return node bin command list for subprocess execution."""
    if which(NPX_BIN):
        # Use npx if available (npm v5.2+)
        cmd_list = [NPX_BIN, "-c", "%s %s" % (command, " ".join(command_opts))]
    else:
        logger.debug("npx not found; falling back to invoking shell script directly")
        cmd_list = [str(path / "node_modules" / ".bin" / command), *command_opts]
    logger.debug("node command: %s", format_npm_command_for_logging(cmd_list))
    return cmd_list


def run_module_command(
    cmd_list: List[str],
    env_vars: Dict[str, str],
    exit_on_error: bool = True,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> None:
    """Shell out to provisioner command."""
    logger.debug("running command: %s", " ".join(cmd_list))
    if exit_on_error:
        try:
            subprocess.check_call(cmd_list, env=env_vars)
        except subprocess.CalledProcessError as shelloutexc:
            sys.exit(shelloutexc.returncode)
    else:
        subprocess.check_call(cmd_list, env=env_vars)


def use_npm_ci(path: Path) -> bool:
    """Return true if npm ci should be used in lieu of npm install."""
    # https://docs.npmjs.com/cli/ci#description
    with open(os.devnull, "w") as fnull:
        if (
            (
                (path / "package-lock.json").is_file()
                or (path / "npm-shrinkwrap.json").is_file()
            )
            and subprocess.call(
                [NPM_BIN, "ci", "-h"], stdout=fnull, stderr=subprocess.STDOUT
            )
            == 0
        ):
            return True
    return False


def run_npm_install(
    path: Path,
    options: Dict[str, Union[Dict[str, Any], str]],
    context: Context,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> None:
    """Run npm install/ci."""
    # Use npm ci if available (npm v5.7+)
    cmd = [NPM_BIN, "<place-holder>"]
    if context.no_color:
        cmd.append("--no-color")
    if cast(Dict[str, Any], options.get("options", {})).get("skip_npm_ci"):
        logger.info("skipped npm ci/npm install")
        return
    if context.env_vars.get("CI") and use_npm_ci(path):
        logger.info("running npm ci...")
        cmd[1] = "ci"
    else:
        logger.info("running npm install...")
        cmd[1] = "install"
    subprocess.check_call(cmd)


def warn_on_boto_env_vars(env_vars: Dict[str, str]) -> None:
    """Inform user if boto-specific environment variables are in use."""
    # https://github.com/serverless/serverless/issues/2151#issuecomment-255646512
    if env_vars.get("AWS_DEFAULT_PROFILE") and not env_vars.get("AWS_PROFILE"):
        LOGGER.warning(
            "AWS_DEFAULT_PROFILE environment variable is set "
            "during use of nodejs-based module and AWS_PROFILE is "
            "not set -- you likely want to set AWS_PROFILE instead"
        )


class RunwayModule:
    """Base class for Runway modules."""

    context: Context
    logger: Union[PrefixAdaptor, RunwayLogger]
    name: str

    def __init__(
        self,
        context: Context,
        path: Path,
        options: Optional[Dict[str, Union[Dict[str, Any], str]]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.
            path: Path to the module.
            options: Everything in the module definition merged with applicable
                values from the deployment definition.

        """
        self.context = context
        self.logger = LOGGER
        self.path = str(path)
        self.options = {} if options is None else options
        self.name = cast(str, self.options.get("name", path.name))

    # the rest of these 'abstract' methods must have names which match
    #  the commands defined in `cli.py`

    def plan(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the plan() method yourself!")

    def deploy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the deploy() method yourself!")

    def destroy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the destroy() method yourself!")

    def __getitem__(self, key: str) -> Any:
        """Make the object subscriptable.

        Args:
            key: Attribute to get.

        """
        return getattr(self, key)


class RunwayModuleNpm(RunwayModule):  # pylint: disable=abstract-method
    """Base class for Runway modules that use npm."""

    # TODO we need a better name than "options" or pass in as kwargs
    def __init__(
        self,
        context: Context,
        path: Path,
        options: Optional[Dict[str, Union[Dict[str, Any], str]]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.
            path: Path to the module.
            options: Everything in the module definition merged with applicable
                values from the deployment definition.

        """
        options = options or {}
        super().__init__(context, path, options)
        del self.options  # remove the attr set by the parent class

        # potential future state of RunwayModule attributes in a future release
        self._raw_path = (
            Path(cast(str, options.pop("path"))) if options.get("path") else None
        )
        self.environments = cast(Dict[str, Any], options.pop("environments", {}))
        self.options = cast(Dict[str, Any], options.pop("options", {}))
        self.parameters = cast(Dict[str, Any], options.pop("parameters", {}))
        self.path = path if isinstance(self.path, Path) else Path(self.path)

        for k, v in options.items():
            setattr(self, k, v)

        self.check_for_npm()  # fail fast
        warn_on_boto_env_vars(self.context.env_vars)

    def check_for_npm(self) -> None:
        """Ensure npm is installed and in the current path."""
        if not which("npm"):
            self.logger.error(
                '"npm" not found in path or is not executable; '
                "please ensure it is installed correctly"
            )
            sys.exit(1)

    def log_npm_command(self, command: List[str]) -> None:
        """Log an npm command that is going to be run.

        Args:
            command: List that will be passed into a subprocess.

        """
        self.logger.debug("node command: %s", format_npm_command_for_logging(command))

    def npm_install(self) -> None:
        """Run ``npm install``."""
        cmd = [NPM_BIN, "<place-holder>"]
        if self.context.no_color:
            cmd.append("--no-color")
        if self.options.get("skip_npm_ci"):
            self.logger.info("skipped npm ci/npm install")
            return
        if self.context.is_noninteractive and use_npm_ci(self.path):
            self.logger.info("running npm ci...")
            cmd[1] = "ci"
        else:
            self.logger.info("running npm install...")
            cmd[1] = "install"
        subprocess.check_call(cmd)

    def package_json_missing(self) -> bool:
        """Check for the existence for a package.json file in the module.

        Returns:
            bool: True if the file was not found.

        """
        if not (self.path / "package.json").is_file():
            self.logger.debug("module is missing package.json")
            return True
        return False


class ModuleOptions(MutableMapping):
    """Base class for Runway module options."""

    @staticmethod
    def merge_nested_env_dicts(data: Any, env_name: Optional[str] = None) -> Any:
        """Merge nested env dicts.

        Args:
            data: Data to try to merge.
            env_name: Current environment.

        """
        if isinstance(data, (list, type(None), str)):
            return data
        if isinstance(data, dict):
            return {
                key: merge_nested_environment_dicts(value, env_name)
                for key, value in data.items()
            }
        raise TypeError(
            "expected type of list, NoneType, or str; got type %s" % type(data)
        )

    @classmethod
    def parse(cls, context: Context, **kwargs: Any) -> ModuleOptions:
        """Parse module options definition to extract usable options.

        Args:
            context: Runway context object.

        """
        raise NotImplementedError

    def __delitem__(self, key: str) -> None:
        """Implement deletion of self[key].

        Args:
            key: Attribute name to remove from the object.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                del obj['key']
                print(obj.__dict__)
                # {}

        """
        delattr(self, key)

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            KeyError: Key does not exist in the object.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                print(obj['key'])
                # value

        """
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> Any:
        """Implement assignment to self[key].

        Args:
            key: Attribute name to associate with a value.
            value: Value of a key/attribute.

        Example:
            .. codeblock: python

                obj = ModuleOptions()
                obj['key'] = 'value'
                print(obj['key'])
                # value

        """
        setattr(self, key, value)

    def __len__(self) -> int:
        """Implement the built-in function len().

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                print(len(obj))
                # 1

        """
        return len(self.__dict__)

    def __iter__(self) -> Iterator[str]:
        """Return iterator object that can iterate over all attributes.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                for k, v in obj.items():
                    print(f'{key}: {value}')
                # key: value

        """
        return iter(self.__dict__)
