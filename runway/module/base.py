"""Base classes for runway modules."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from ..exceptions import NpmNotFound
from ..utils import which
from .utils import NPM_BIN, format_npm_command_for_logging, use_npm_ci

if TYPE_CHECKING:
    from .._logging import PrefixAdaptor, RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class RunwayModule:
    """Base class for Runway modules."""

    ctx: RunwayContext
    explicitly_enabled: Optional[bool]
    logger: Union[PrefixAdaptor, RunwayLogger]
    name: str
    options: Union[Dict[str, Any], ModuleOptions]
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
        self.ctx = context
        self.explicitly_enabled = explicitly_enabled
        self.logger = logger
        self.name = name or module_root.name
        self.options = options or {}
        self.parameters = parameters or {}
        self.path = module_root
        self.region = context.env.aws_region

    def deploy(self) -> None:
        """Abstract method called when running deploy."""
        raise NotImplementedError("You must implement the deploy() method yourself!")

    def destroy(self) -> None:
        """Abstract method called when running destroy."""
        raise NotImplementedError("You must implement the destroy() method yourself!")

    def init(self) -> None:
        """Abstract method called when running init."""
        raise NotImplementedError("You must implement the init() method yourself!")

    def plan(self) -> None:
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
        self.warn_on_boto_env_vars(self.ctx.env.vars, logger=logger)

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
        if self.ctx.no_color:
            cmd.append("--no-color")
        if self.ctx.is_noninteractive and use_npm_ci(self.path):
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


class ModuleOptions:
    """Base class for Runway module options."""

    def get(self, name: str, default: Any = None) -> Any:
        """Get a value or return the default."""
        return getattr(self, name, default)

    def __eq__(self, other: Any) -> bool:
        """Assess equality."""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False
