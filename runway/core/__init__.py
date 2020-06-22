"""Core Runway API."""
from typing import TYPE_CHECKING, List, Optional  # noqa pylint: disable=W

from .components import Deployment, DeployEnvironment
from ..context import Context

if TYPE_CHECKING:
    from ..config import Config, DeploymentDefinition


class Runway(object):
    """Runway's core functionality."""

    def __init__(self, config, context=None):
        # type: (Config, Optional[Context]) -> None
        """Instantiate class.

        Args:
            config: Runway config.
            context: Runway context.

        """
        self.deployments = config.deployments
        self.future = config.future
        self.tests = config.tests
        self.ignore_git_branch = config.ignore_git_branch
        self.variables = config.variables

        if context:
            self.ctx = context
        else:
            self.ctx = Context(
                deploy_environment=DeployEnvironment(
                    ignore_git_branch=self.ignore_git_branch
                )
            )
        self.ctx.env.log_name()

    def deploy(self, deployments=None):
        # type: (Optional[List[DeploymentDefinition]]) -> None
        """Deploy action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run.

        """
        self.ctx.command = 'deploy'
        Deployment.run_list(action='deploy',
                            context=self.ctx,
                            deployments=deployments or self.deployments,
                            variables=self.variables)

    def destory(self):
        """Destroy action."""
