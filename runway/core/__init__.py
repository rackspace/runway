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
        self.__run_action('deploy', deployments if deployments is not None else
                          self.deployments)

    def destroy(self, deployments=None):
        # type: (Optional[List[DeploymentDefinition]]) -> None
        """Destroy action.

        Args:
            deployments: List of deployments to run. If not provided,
                all deployments in the config will be run in reverse.

        """
        self.__run_action('destroy', deployments if deployments is not None else
                          self.reverse_deployments(self.deployments))
        if not deployments:
            # return config attribute to original state
            self.reverse_deployments(self.deployments)

    @staticmethod
    def reverse_deployments(deployments):
        # type: (List[DeploymentDefinition]) -> List[DeploymentDefinition]
        """Reverse deployments and the modules within them.

        Args:
            deployments: List of deployments to reverse.

        Returns:
            Deployments and modules in reverse order.

        """
        result = []
        for deployment in deployments:
            deployment.reverse()
            result.insert(0, deployment)
        return result

    def __run_action(self, action, deployments):
        # type: (Optional[List[DeploymentDefinition]]) -> None
        """Run an action on a list of deployments.

        Args:
            action: Name of the action.
            deployments: List of deployments to run.

        """
        self.ctx.command = action
        Deployment.run_list(action=action,
                            context=self.ctx,
                            deployments=deployments,
                            future=self.future,
                            variables=self.variables)
