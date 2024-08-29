"""Python project."""

from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING, ClassVar

from .....compat import cached_property
from .....dependency_managers import (
    Pip,
    Pipenv,
    PipenvNotFoundError,
    Poetry,
    PoetryNotFoundError,
)
from ..base_classes import Project
from ..models.args import PythonHookArgs
from . import PythonDockerDependencyInstaller

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import Literal

LOGGER = logging.getLogger(__name__.replace("._", "."))


class PythonProject(Project[PythonHookArgs]):
    """Python project."""

    DEFAULT_CACHE_DIR_NAME: ClassVar[str] = "pip_cache"
    """Name of the default cache directory."""

    @cached_property
    def docker(self) -> PythonDockerDependencyInstaller | None:
        """Docker interface that can be used to build the project."""
        return PythonDockerDependencyInstaller.from_project(self)

    @cached_property
    def metadata_files(self) -> tuple[Path, ...]:
        """Project metadata files.

        Files are only included in return value if they exist.

        """
        if self.project_type == "poetry":
            config_files = [self.project_root / config_file for config_file in Poetry.CONFIG_FILES]
        elif self.project_type == "pipenv":
            config_files = [self.project_root / config_file for config_file in Pipenv.CONFIG_FILES]
        else:
            config_files = [self.project_root / config_file for config_file in Pip.CONFIG_FILES]
        return tuple(path for path in config_files if path.exists())

    @cached_property
    def runtime(self) -> str:
        """Runtime of the build system.

        Value should be a valid Lambda Function runtime
        (https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

        """
        if self._runtime_from_docker:
            return self._validate_runtime(self._runtime_from_docker)
        return self._validate_runtime(
            f"python{self.pip.python_version.major}.{self.pip.python_version.minor}"
        )

    @cached_property
    def pip(self) -> Pip:
        """Pip dependency manager."""
        return Pip(self.ctx, self.project_root)

    @cached_property
    def pipenv(self) -> Pipenv | None:
        """Pipenv dependency manager.

        Return:
            If the project uses pipenv and pipenv is not explicitly disabled,
            an object for interfacing with pipenv will be returned.

        Raises:
            PipenvNotFoundError: pipenv is not installed or not found in PATH.

        """
        if self.project_type != "pipenv":
            return None
        if Pipenv.found_in_path():
            return Pipenv(self.ctx, self.project_root)
        raise PipenvNotFoundError

    @cached_property
    def poetry(self) -> Poetry | None:
        """Poetry dependency manager.

        Return:
            If the project uses poetry and poetry is not explicitly disabled,
            an object for interfacing with poetry will be returned.

        Raises:
            PoetryNotFound: poetry is not installed or not found in PATH.

        """
        if self.project_type != "poetry":
            return None
        if Poetry.found_in_path():
            return Poetry(self.ctx, self.project_root)
        raise PoetryNotFoundError

    @cached_property
    def project_type(self) -> Literal["pip", "pipenv", "poetry"]:
        """Type of python project."""
        if Poetry.dir_is_project(self.project_root):
            if self.args.use_poetry:
                return "poetry"
            LOGGER.warning("poetry project detected but use of poetry is explicitly disabled")
        if Pipenv.dir_is_project(self.project_root):
            if self.args.use_pipenv:
                return "pipenv"
            LOGGER.warning("pipenv project detected but use of pipenv is explicitly disabled")
        return "pip"

    @cached_property
    def requirements_txt(self) -> Path | None:
        """Dependency file for the project."""
        if self.poetry:  # prioritize poetry
            return self.poetry.export(output=self.tmp_requirements_txt)
        if self.pipenv:
            return self.pipenv.export(output=self.tmp_requirements_txt)
        requirements_txt = self.project_root / "requirements.txt"
        if Pip.dir_is_project(self.project_root, file_name=requirements_txt.name):
            return requirements_txt
        return None

    @cached_property
    def supported_metadata_files(self) -> set[str]:
        """Names of all supported metadata files.

        Returns:
            Set of file names - not paths.

        """
        file_names = {*Pip.CONFIG_FILES}
        if self.args.use_poetry:
            file_names.update(Poetry.CONFIG_FILES)
        if self.args.use_pipenv:
            file_names.update(Pipenv.CONFIG_FILES)
        return file_names

    @cached_property
    def tmp_requirements_txt(self) -> Path:
        """Temporary requirements.txt file.

        This path is only used when exporting from another format.

        """
        return self.ctx.work_dir / f"{self.source_code.md5_hash}.requirements.txt"

    def cleanup(self) -> None:
        """Cleanup temporary files after the build process has run."""
        if (self.poetry or self.pipenv) and self.tmp_requirements_txt.exists():
            self.tmp_requirements_txt.unlink()
        shutil.rmtree(self.dependency_directory, ignore_errors=True)
        if not any(self.build_directory.iterdir()):
            # remove build_directory if it's empty
            shutil.rmtree(self.build_directory, ignore_errors=True)

    def install_dependencies(self) -> None:
        """Install project dependencies."""
        if self.requirements_txt:
            LOGGER.debug("installing dependencies to %s...", self.dependency_directory)
            if self.docker:
                self.docker.install()
            else:
                self.pip.install(
                    cache_dir=self.args.cache_dir,
                    extend_args=self.args.extend_pip_args,
                    no_cache_dir=not self.args.use_cache,
                    no_deps=bool(self.poetry or self.pipenv),
                    requirements=self.requirements_txt,
                    target=self.dependency_directory,
                )
            LOGGER.debug("dependencies successfully installed to %s", self.dependency_directory)
        else:
            LOGGER.info("skipped installing dependencies; none found")
