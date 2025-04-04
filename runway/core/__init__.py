"""Core Runway API."""

from __future__ import annotations

import logging as _logging
import sys as _sys
import traceback as _traceback
from typing import TYPE_CHECKING, Any, cast

import yaml as _yaml

from .. import __version__
from .._logging import PrefixAdaptor as _PrefixAdaptor
from .._logging import RunwayLogger as _RunwayLogger
from ..utils import DOC_SITE
from ..utils import YamlDumper as _YamlDumper
from . import components, providers, type_defs

if TYPE_CHECKING:
    from ..config import RunwayConfig
    from ..config.components.runway import RunwayDeploymentDefinition
    from ..context import RunwayContext

LOGGER = cast("_RunwayLogger", _logging.getLogger(__name__))

__all__ = ["Runway", "components", "providers", "type_defs"]


class Runway:
    """Runway's core functionality."""

    def __init__(self, config: RunwayConfig, context: RunwayContext) -> None:
        """Instantiate class.

        Args:
            config: Runway config.
            context: Runway context.

        """
        self.ctx = context
        self.deployments = config.deployments
        self.future = config.future
        self.required_version = config.runway_version
        self.ignore_git_branch = config.ignore_git_branch
        self.variables = config.variables
        self.__assert_config_version()
        self.ctx.env.log_name()

    def deploy(self, deployments: list[RunwayDeploymentDefinition] | None = None) -> None:
        """Deploy action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run.

        """
        self.__run_action("deploy", deployments if deployments is not None else self.deployments)

    def destroy(self, deployments: list[RunwayDeploymentDefinition] | None = None) -> None:
        """Destroy action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run in reverse.

        """
        self.__run_action(
            "destroy",
            (
                deployments
                if deployments is not None
                else self.reverse_deployments(self.deployments)
            ),
        )
        if not deployments:
            # return config attribute to original state
            self.reverse_deployments(self.deployments)

    def get_env_vars(
        self, deployments: list[RunwayDeploymentDefinition] | None = None
    ) -> dict[str, Any]:
        """Get env_vars defined in the config.

        Args:
            deployments: List of deployments to get env_vars from.

        Returns:
            Resolved env_vars from the deployments.

        """
        deployments = deployments or self.deployments
        result: dict[str, str] = {}
        for deployment in deployments:
            obj = components.Deployment(
                context=self.ctx, definition=deployment, variables=self.variables
            )
            result.update(obj.env_vars_config)
        return result

    def init(self, deployments: list[RunwayDeploymentDefinition] | None = None) -> None:
        """Init action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run.

        """
        self.__run_action("init", deployments if deployments is not None else self.deployments)

    def plan(self, deployments: list[RunwayDeploymentDefinition] | None = None) -> None:
        """Plan action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run.

        """
        self.__run_action("plan", deployments if deployments is not None else self.deployments)

    @staticmethod
    def reverse_deployments(
        deployments: list[RunwayDeploymentDefinition],
    ) -> list[RunwayDeploymentDefinition]:
        """Reverse deployments and the modules within them.

        Args:
            deployments: List of deployments to reverse.

        Returns:
            Deployments and modules in reverse order.

        """
        result: list[RunwayDeploymentDefinition] = []
        for deployment in deployments:
            deployment.reverse()
            result.insert(0, deployment)
        return result

    def __assert_config_version(self) -> None:
        """Assert the config supports this version of Runway."""
        if not self.required_version:
            LOGGER.debug("required Runway version not specified")
            return
        if __version__ in self.required_version:
            LOGGER.debug(
                'current Runway version "%s" matches "%s" required by this config file',
                __version__,
                self.required_version,
            )
            return
        if __version__.startswith("0.") and "dev" in __version__:
            LOGGER.warning(
                "Runway is being used from a shallow clone of the repo; "
                "config version will not be enforced as version cannot be determined"
            )
            return
        LOGGER.error(
            'current Runway version "%s" does not match "%s" required by this config file',
            __version__,
            self.required_version,
        )
        _sys.exit(1)

    def __run_action(
        self,
        action: type_defs.RunwayActionTypeDef,
        deployments: list[RunwayDeploymentDefinition] | None,
    ) -> None:
        """Run an action on a list of deployments.

        Args:
            action: Name of the action.
            deployments: List of deployments to run.

        """
        self.ctx.command = action
        components.Deployment.run_list(
            action=action,
            context=self.ctx,
            deployments=deployments or [],
            future=self.future,
            variables=self.variables,
        )
