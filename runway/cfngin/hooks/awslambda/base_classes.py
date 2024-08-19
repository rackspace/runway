"""Base classes."""

from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    TypeVar,
    cast,
    overload,
)

from ....compat import cached_property
from ..protocols import CfnginHookProtocol
from .exceptions import RuntimeMismatchError
from .models.args import AwsLambdaHookArgs
from .models.responses import AwsLambdaHookDeployResponse
from .source_code import SourceCode

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import Literal

    from ...._logging import RunwayLogger
    from ....context import CfnginContext
    from ....utils import BaseModel
    from .deployment_package import DeploymentPackage
    from .docker import DockerDependencyInstaller
    from .type_defs import AwsLambdaHookDeployResponseTypedDict

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))

_AwsLambdaHookArgsTypeVar_co = TypeVar(
    "_AwsLambdaHookArgsTypeVar_co", bound=AwsLambdaHookArgs, covariant=True
)


class Project(Generic[_AwsLambdaHookArgsTypeVar_co]):
    """Project containing source code for an AWS Lambda Function."""

    DEFAULT_CACHE_DIR_NAME: ClassVar[str] = "cache"
    """Name of the default cache directory."""

    args: _AwsLambdaHookArgsTypeVar_co
    """Parsed hook arguments."""

    ctx: CfnginContext
    """CFNgin context object."""

    def __init__(self, args: _AwsLambdaHookArgsTypeVar_co, context: CfnginContext) -> None:
        """Instantiate class.

        Args:
            args: Parsed hook arguments.
            context: Context object.

        """
        self.args = args
        self.ctx = context

    @cached_property
    def build_directory(self) -> Path:
        """Directory being used to build deployment package."""
        result = (
            self.ctx.work_dir
            / f"{self.source_code.root_directory.name}.{self.source_code.md5_hash}"
        )
        result.mkdir(exist_ok=True, parents=True)
        return result

    @cached_property
    def cache_dir(self) -> Path | None:
        """Directory where a dependency manager's cache data will be stored.

        Returns:
            Explicit cache directory if provided or default cache directory if
            it is not provided. If configured to not use cache, will always be
            ``None``.

        """
        if not self.args.use_cache:
            return None
        cache_dir = (
            self.args.cache_dir
            if self.args.cache_dir
            else self.ctx.work_dir / self.DEFAULT_CACHE_DIR_NAME
        )
        cache_dir.mkdir(exist_ok=True, parents=True)
        return cache_dir

    @cached_property
    def compatible_architectures(self) -> list[str] | None:
        """List of compatible instruction set architectures."""
        return getattr(self.args, "compatible_architectures", None)

    @cached_property
    def compatible_runtimes(self) -> list[str] | None:
        """List of compatible runtimes.

        Value should be valid Lambda Function runtimes
        (https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

        Raises:
            ValueError: Defined or detected runtime is not in the list of
                compatible runtimes.

        """
        runtimes = getattr(self.args, "compatible_runtimes", cast("list[str]", []))
        if runtimes and self.runtime not in runtimes:
            raise ValueError(
                f"runtime ({self.runtime}) not in compatible runtimes ({', '.join(runtimes)})"
            )
        return runtimes

    @cached_property
    def dependency_directory(self) -> Path:
        """Directory to use as the target of ``pip install --target``."""
        result = self.build_directory / "dependencies"
        result.mkdir(exist_ok=True, parents=True)
        return result

    @cached_property
    def license(self) -> str | None:
        """Software license for the project.

        Can be any of the following:

        - A SPDX license identifier (e.g. ``MIT``).
        - The URL of a license hosted on the internet (e.g.
          ``https://opensource.org/licenses/MIT``).
        - The full text of the license.

        """
        return getattr(self.args, "license", None)

    @cached_property
    def metadata_files(self) -> tuple[Path, ...]:
        """Project metadata files (e.g. ``project.json``, ``pyproject.toml``)."""
        return ()

    @cached_property
    def runtime(self) -> str:
        """runtime of the build system.

        Value should be a valid Lambda Function runtime
        (https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

        This property can be overwritten by subclasses when runtime can be
        determined through additional means.

        """
        if self._runtime_from_docker:
            return self._validate_runtime(self._runtime_from_docker)
        raise ValueError("runtime could not be determined from the build system")

    @cached_property
    def _runtime_from_docker(self) -> str | None:
        """runtime from Docker if class can use Docker."""
        docker: DockerDependencyInstaller | None = getattr(self, "docker", None)
        if not docker:
            return None
        return docker.runtime

    def _validate_runtime(self, detected_runtime: str) -> str:
        """Verify that the detected runtime matches what is explicitly defined.

        This method should be used before returning the detected runtime from
        the ``.runtime`` property.

        Args:
            detected_runtime: The runtime detected from the build system.

        Raises:
            RuntimeMismatchError: The detected runtime does not match what is
                defined.

        """
        if self.args.runtime and self.args.runtime != detected_runtime:
            raise RuntimeMismatchError(self.args.runtime, detected_runtime)
        return detected_runtime

    @cached_property
    def source_code(self) -> SourceCode:
        """Project source code.

        Lazy load source code object.
        Extends gitignore as needed.

        """
        source_code = SourceCode(
            self.args.source_code,
            include_files_in_hash=self.metadata_files,
            project_root=self.project_root,
        )
        for rule in self.args.extend_gitignore:
            source_code.add_filter_rule(rule)
        return source_code

    @cached_property
    def project_root(self) -> Path:
        """Root directory of the project.

        The top-level directory containing the source code and all
        configuration/metadata files (e.g. pyproject.toml, package.json).

        The project root can be different from the source code directory but,
        if they are different, the project root should contain the source code
        directory. If it does not, the source code directory will be always
        be used.

        The primary use case for this property is to allow configuration files
        to exist outside of the source code directory. The ``project_type``
        can and should rely on the value of this property when determining the
        type.

        """
        top_lvl_dir = (
            self.ctx.config_path.parent
            if self.ctx.config_path.is_file()
            else (self.ctx.config_path if self.ctx.config_path.is_dir() else self.args.source_code)
        )
        if top_lvl_dir == self.args.source_code:
            return top_lvl_dir

        parents = list(self.args.source_code.parents)
        if top_lvl_dir not in parents:
            LOGGER.info(
                "ignoring project directory; source code located outside of project directory"
            )
            return self.args.source_code

        dirs_to_check = [
            self.args.source_code,
            *parents[: parents.index(top_lvl_dir) + 1],
        ]
        for dir_to_check in dirs_to_check:
            for check_for_file in self.supported_metadata_files:
                if next(dir_to_check.glob(check_for_file), None):
                    return dir_to_check
        # reached if all dirs in between source and top-level are missing metadata files
        return top_lvl_dir

    @cached_property
    def project_type(self) -> str:
        """Type of project (e.g. poetry, yarn).

        This should be considered more of a "subtype" as the subclass should
        distinguish project language. The value of this property should reflect
        the project/dependency management tool used within the project.

        The value of this property should be calculated without initializing
        other properties (e.g. ``source_code``) except for ``project_root``
        so that it can be used in their initialization process.

        """
        raise NotImplementedError

    @cached_property
    def supported_metadata_files(self) -> set[str]:
        """Names of all supported metadata files.

        Returns:
            Set of file names - not paths.

        """
        return set()

    def cleanup(self) -> None:
        """Cleanup project files at the end of execution.

        If any cleanup is needed (e.g. removal of temporary dependency directory)
        it should be implimented here. Hook's should call this method in a
        ``finally`` block to ensure it is run even if the rest of the hook
        encountered an error.

        """

    def cleanup_on_error(self) -> None:
        """Cleanup project files when an error occurs.

        This will be run before ``self.cleanup()`` if an error has occurred.

        Hooks should call this method in an ``except`` block and reraise the
        error afterward.

        """

    def install_dependencies(self) -> None:
        """Install project dependencies.

        Arguments/options should be read from the ``args`` attribute of this
        object instead of being passed into the method call. The method itself
        only exists for timing and filling in custom handling that is required
        for each project type.

        """
        raise NotImplementedError


_ProjectTypeVar = TypeVar("_ProjectTypeVar", bound=Project[AwsLambdaHookArgs])


class AwsLambdaHook(CfnginHookProtocol, Generic[_ProjectTypeVar]):
    """Base class for AWS Lambda hooks."""

    BUILD_LAYER: ClassVar[bool] = False
    """Flag to denote if the hook creates a Lambda Function or Layer deployment package."""

    ctx: CfnginContext
    """CFNgin context object."""

    def __init__(self, context: CfnginContext, **_kwargs: Any) -> None:
        """Instantiate class.

        This method should be overridden by subclasses.
        This is required to set the value of the args attribute.

        Args:
            context: CFNgin context object (passed in by CFNgin).

        """
        self.ctx = context

    @cached_property
    def deployment_package(self) -> DeploymentPackage[_ProjectTypeVar]:
        """AWS Lambda deployment package."""
        raise NotImplementedError

    @cached_property
    def project(self) -> _ProjectTypeVar:
        """Project being deployed as an AWS Lambda Function."""
        raise NotImplementedError

    @overload
    def build_response(self, stage: Literal["deploy"]) -> AwsLambdaHookDeployResponse: ...

    @overload
    def build_response(self, stage: Literal["destroy"]) -> BaseModel | None: ...

    @overload
    def build_response(self, stage: Literal["plan"]) -> AwsLambdaHookDeployResponse: ...

    def build_response(self, stage: Literal["deploy", "destroy", "plan"]) -> BaseModel | None:
        """Build response object that will be returned by this hook.

        Args:
            stage: The current stage being executed by the hook.

        """
        if stage == "deploy":
            return self._build_response_deploy()
        if stage == "destroy":
            return self._build_response_destroy()
        if stage == "plan":
            return self._build_response_plan()
        raise NotImplementedError("only deploy and destroy are supported")

    def _build_response_deploy(self) -> AwsLambdaHookDeployResponse:
        """Build response for deploy stage."""
        return AwsLambdaHookDeployResponse(
            bucket_name=self.deployment_package.bucket.name,
            code_sha256=self.deployment_package.code_sha256,
            compatible_architectures=self.deployment_package.compatible_architectures,
            compatible_runtimes=self.deployment_package.compatible_runtimes,
            license=self.deployment_package.license,
            object_key=self.deployment_package.object_key,
            object_version_id=self.deployment_package.object_version_id,
            runtime=self.deployment_package.runtime,
        )

    def _build_response_destroy(self) -> BaseModel | None:
        """Build response for destroy stage."""
        return None

    def _build_response_plan(self) -> AwsLambdaHookDeployResponse:
        """Build response for plan stage."""
        try:
            return AwsLambdaHookDeployResponse(
                bucket_name=self.deployment_package.bucket.name,
                code_sha256=self.deployment_package.code_sha256,
                compatible_architectures=self.deployment_package.compatible_architectures,
                compatible_runtimes=self.deployment_package.compatible_runtimes,
                license=self.deployment_package.license,
                object_key=self.deployment_package.object_key,
                object_version_id=self.deployment_package.object_version_id,
                runtime=self.deployment_package.runtime,
            )
        except FileNotFoundError:
            return AwsLambdaHookDeployResponse(
                bucket_name=self.deployment_package.bucket.name,
                code_sha256="WILL CALCULATE WHEN BUILT",
                compatible_architectures=self.deployment_package.compatible_architectures,
                compatible_runtimes=self.deployment_package.compatible_runtimes,
                license=self.deployment_package.license,
                object_key=self.deployment_package.object_key,
                object_version_id=self.deployment_package.object_version_id,
                runtime=self.deployment_package.runtime,
            )

    def cleanup(self) -> None:
        """Cleanup temporary files at the end of execution.

        If any cleanup is needed (e.g. removal of temporary dependency directory)
        it should be implimented here. A Hook's stage methods should call this
        method in a ``finally`` block to ensure it is run even if the rest of
        the hook encountered an error.

        .. rubric:: Example
        .. code-block:: python

            def pre_deploy(self) -> Any:
                try:
                    pass  # primary logic
                except BaseException:
                    self.cleanup_on_error()
                    raise
                finally:
                    self.cleanup()

        """

    def cleanup_on_error(self) -> None:
        """Cleanup temporary files when an error occurs.

        This will be run before ``self.cleanup()`` if an error has occurred.

        A Hook's stage method should call this method in an ``except`` block
        and reraise the error afterward.

        .. rubric:: Example
        .. code-block:: python

            def pre_deploy(self) -> Any:
                try:
                    pass  # primary logic
                except BaseException:
                    self.cleanup_on_error()
                    raise
                finally:
                    self.cleanup()

        """

    def plan(self) -> AwsLambdaHookDeployResponseTypedDict:
        """Run during the **plan** stage."""
        return cast(
            "AwsLambdaHookDeployResponseTypedDict",
            self.build_response("plan").model_dump(by_alias=True),
        )

    def post_deploy(self) -> Any:
        """Run during the **post_deploy** stage."""
        LOGGER.warning("post_deploy not implimented for %s", self.__class__.__name__)
        return True

    def post_destroy(self) -> Any:
        """Run during the **post_destroy** stage."""
        LOGGER.warning("post_destroy not implimented for %s", self.__class__.__name__)
        return True

    def pre_deploy(self) -> Any:
        """Run during the **pre_deploy** stage."""
        LOGGER.warning("pre_deploy not implimented for %s", self.__class__.__name__)
        return True

    def pre_destroy(self) -> Any:
        """Run during the **pre_destroy** stage."""
        LOGGER.warning("pre_destroy not implimented for %s", self.__class__.__name__)
        return True
