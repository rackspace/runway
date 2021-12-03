"""Docker logic for python."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from docker.types.services import Mount

from .....compat import cached_property, shlex_join
from .....utils import Version
from ..docker import DockerDependencyInstaller

if TYPE_CHECKING:
    from docker.client import DockerClient

    from .....context import CfnginContext, RunwayContext
    from . import PythonProject


class PythonDockerDependencyInstaller(DockerDependencyInstaller):
    """Docker dependency installer for Python."""

    project: PythonProject

    def __init__(
        self,
        project: PythonProject,
        *,
        client: Optional[DockerClient] = None,
        context: Optional[Union[CfnginContext, RunwayContext]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            project: awslambda project.
            client: Pre-configured :class:`docker.client.DockerClient`.
            context: CFNgin or Runway context object.

        """
        super().__init__(project, client=client, context=context)

    @cached_property
    def bind_mounts(self) -> List[Mount]:
        """Bind mounts that will be used by the container."""
        mounts = [*super().bind_mounts]
        if self.project.requirements_txt:
            mounts.append(
                Mount(
                    target=f"/var/task/{self.project.requirements_txt.name}",
                    source=str(self.project.requirements_txt),
                    type="bind",
                )
            )
        return mounts

    @cached_property
    def environmet_variables(self) -> Dict[str, str]:
        """Environment variables to pass to the docker container.

        This is a subset of the environment variables stored in the context
        object as some will cause issues if they are passed.

        """
        docker_env_vars = super().environmet_variables
        pip_env_vars = {
            k: v for k, v in self.ctx.env.vars.items() if k.startswith("PIP")
        }
        return {**docker_env_vars, **pip_env_vars}

    @cached_property
    def install_commands(self) -> List[str]:
        """Commands to run to install dependencies."""
        if self.project.requirements_txt:
            return [
                shlex_join(
                    self.project.pip.generate_install_command(
                        cache_dir=self.CACHE_DIR if self.project.cache_dir else None,
                        no_cache_dir=not self.project.args.use_cache,
                        no_deps=bool(self.project.poetry or self.project.pipenv),
                        requirements=f"/var/task/{self.project.requirements_txt.name}",
                        target=self.DEPENDENCY_DIR,
                    )
                    + (self.project.args.extend_pip_args or [])
                )
            ]
        return []

    @cached_property
    def python_version(self) -> Optional[Version]:
        """Version of Python installed in the docker container."""
        match = re.search(
            r"Python (?P<version>\S*)",
            "\n".join(self.run_command("python --version", level=logging.DEBUG)),
        )
        if not match:
            return None
        return Version(match.group("version"))

    @cached_property
    def runtime(self) -> Optional[str]:
        """AWS Lambda runtime determined from the docker container's Python version."""
        if not self.python_version:
            return None
        return f"python{self.python_version.major}.{self.python_version.minor}"
