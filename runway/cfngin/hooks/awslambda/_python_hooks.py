"""Hook for creating an AWS Lambda Function using Python runtime."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from ....compat import cached_property
from .base_classes import AwsLambdaHook
from .models.args import PythonHookArgs
from .python_requirements import PythonDeploymentPackage, PythonProject

if TYPE_CHECKING:
    from ....context import CfnginContext
    from .base_classes import DeploymentPackage

LOGGER = logging.getLogger(__name__.replace("._", "."))


class PythonFunction(AwsLambdaHook[PythonProject]):
    """Hook for creating an AWS Lambda Function using Python runtime."""

    BUILD_LAYER: ClassVar[bool] = False
    """Flag to denote that this hook creates a Lambda Function deployment package."""

    args: PythonHookArgs
    """Parsed hook arguments."""

    def __init__(self, context: CfnginContext, **kwargs: Any) -> None:
        """Instantiate class."""
        super().__init__(context)
        self.args = PythonHookArgs.model_validate(kwargs)

    @cached_property
    def deployment_package(self) -> DeploymentPackage[PythonProject]:
        """AWS Lambda deployment package."""
        return PythonDeploymentPackage.init(
            self.project, "layer" if self.BUILD_LAYER else "function"
        )

    @cached_property
    def project(self) -> PythonProject:
        """Project being deployed as an AWS Lambda Function."""
        return PythonProject(self.args, self.ctx)

    def cleanup(self) -> None:
        """Cleanup after execution."""
        self.project.cleanup()

    def cleanup_on_error(self) -> None:
        """Cleanup after an error has occurred."""
        self.deployment_package.delete()
        self.project.cleanup_on_error()

    def pre_deploy(self) -> Any:
        """Run during the **pre_deploy** stage."""
        try:
            self.deployment_package.upload()
            return self.build_response("deploy").model_dump(by_alias=True)
        except BaseException:
            self.cleanup_on_error()
            raise
        finally:
            self.cleanup()


class PythonLayer(PythonFunction):
    """Hook for creating an AWS Lambda Layer using Python runtime."""

    BUILD_LAYER: ClassVar[bool] = True
    """Flag to denote that this hook creates a Lambda Layer deployment package."""
