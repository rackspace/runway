"""Base classes for runway modules."""
from __future__ import annotations

import logging
import subprocess
from collections.abc import MutableMapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union, cast

from ..exceptions import NpmNotFound
from ..util import merge_nested_environment_dicts, which
from .utils import NPM_BIN, format_npm_command_for_logging, use_npm_ci

if TYPE_CHECKING:
    from .._logging import PrefixAdaptor, RunwayLogger
    from ..context.runway import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class RunwayModule:
    """Base class for Runway modules."""

    context: RunwayContext
    explicitly_enabled: Optional[bool]
    logger: Union[PrefixAdaptor, RunwayLogger]
    name: str
    options: Union[Dict[str, Any], ModuleOptions]
    parameters: Dict[str, Any]
    region: str

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        self.context = context
        self.explicitly_enabled = explicitly_enabled
        self.logger = logger
        self.name = name or module_root.name
        self.options = options or {}
        self.parameters = parameters or {}
        self.path = module_root
        self.region = context.env.aws_region

    def deploy(self):
        """Abstract method called when running deploy."""
        raise NotImplementedError("You must implement the deploy() method yourself!")

    def destroy(self):
        """Abstract method called when running destroy."""
        raise NotImplementedError("You must implement the destroy() method yourself!")

    def plan(self):
        """Abstract method called when running plan."""
        raise NotImplementedError("You must implement the plan() method yourself!")

    def __getitem__(self, key: str) -> Any:
        """Make the object subscriptable.

        Args:
            key: Attribute to get.

        """
        return getattr(self, key)


class RunwayModuleNpm(RunwayModule):  # pylint: disable=abstract-method
    """Base class for Runway modules that use npm."""

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=options,
            parameters=parameters,
        )
        self.check_for_npm(logger=self.logger)  # fail fast
        self.warn_on_boto_env_vars(self.context.env.vars, logger=logger)

    def log_npm_command(self, command: List[str]) -> None:
        """Log an npm command that is going to be run.

        Args:
            command: List that will be passed into a subprocess.

        """
        self.logger.debug("node command: %s", format_npm_command_for_logging(command))

    def npm_install(self) -> None:
        """Run ``npm install``."""
        if self.options.get("skip_npm_ci"):
            self.logger.info("skipped npm ci/npm install")
            return
        cmd = [NPM_BIN, "<place-holder>"]
        if self.context.no_color:
            cmd.append("--no-color")
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

    @staticmethod
    def check_for_npm(
        *, logger: Union[logging.Logger, PrefixAdaptor, RunwayLogger] = LOGGER
    ) -> None:
        """Ensure npm is installed and in the current path.

        Args:
            logger: Optionally provide a custom logger to use.

        """
        if not which("npm"):
            logger.error(
                '"npm" not found in path or is not executable; '
                "please ensure it is installed correctly"
            )
            raise NpmNotFound

    @staticmethod
    def warn_on_boto_env_vars(
        env_vars: Dict[str, str],
        *,
        logger: Union[logging.Logger, PrefixAdaptor, RunwayLogger] = LOGGER,
    ) -> None:
        """Inform user if boto-specific environment variables are in use.

        Args:
            env_vars: Environment variables to check.
            logger: Optionally provide a custom logger to use.

        """
        # https://github.com/serverless/serverless/issues/2151#issuecomment-255646512
        if env_vars.get("AWS_DEFAULT_PROFILE") and not env_vars.get("AWS_PROFILE"):
            logger.warning(
                "AWS_DEFAULT_PROFILE environment variable is set "
                "during use of nodejs-based module and AWS_PROFILE is "
                "not set -- you likely want to set AWS_PROFILE instead"
            )


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
    def parse(cls, context: RunwayContext, **kwargs: Any) -> ModuleOptions:
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
