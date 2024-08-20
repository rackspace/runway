"""pip CLI interface."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast

from ..compat import cached_property, shlex_join
from ..exceptions import RunwayError
from ..utils import Version
from .base_classes import DependencyManager

if TYPE_CHECKING:
    from collections.abc import Iterable

    from _typeshed import StrPath

    from .._logging import RunwayLogger


LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class PipInstallFailedError(RunwayError):
    """Pip install failed."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class. All args/kwargs are passed to parent method."""
        self.message = (
            "pip failed to install dependencies; review pip's output above to troubleshoot"
        )
        super().__init__(*args, **kwargs)


class Pip(DependencyManager):
    """pip CLI interface."""

    CONFIG_FILES: ClassVar[tuple[str, ...]] = ("requirements.txt",)
    """Configuration files used by pip."""

    EXECUTABLE: ClassVar[str] = "pip"
    """CLI executable."""

    @cached_property
    def python_version(self) -> Version:
        """Python version where pip is installed (``<major>.<minor>`` only)."""
        cmd_output = self._run_command([self.EXECUTABLE, "--version"])
        match = re.search(r"^pip \S* from .+ \(python (?P<version>\S*)\)$", cmd_output)
        if not match:
            LOGGER.warning("unable to parse Python version from output:\n%s", cmd_output)
            return Version("0.0.0")
        return Version(match.group("version"))

    @cached_property
    def version(self) -> Version:
        """pip version."""
        cmd_output = self._run_command([self.EXECUTABLE, "--version"])
        match = re.search(r"^pip (?P<version>\S*) from .+$", cmd_output)
        if not match:
            LOGGER.warning("unable to parse pip version from output:\n%s", cmd_output)
            return Version("0.0.0")
        return Version(match.group("version"))

    @classmethod
    def dir_is_project(cls, directory: StrPath, **kwargs: Any) -> bool:
        """Determine if the directory contains a project for this dependency manager.

        Args:
            directory: Directory to check.
            **kwargs: Arbitrary keyword arguments.

        """
        kwargs.setdefault("file_name", cls.CONFIG_FILES[0])
        requirements_txt = Path(directory) / kwargs["file_name"]
        return bool(requirements_txt.is_file())

    @classmethod
    def generate_install_command(
        cls,
        *,
        cache_dir: StrPath | None = None,
        no_cache_dir: bool = False,
        no_deps: bool = False,
        requirements: StrPath,
        target: StrPath,
    ) -> list[str]:
        """Generate the command that when run will install dependencies.

        This method is exposed to easily format the command to be run by with
        a subprocess or within a Docker container.

        Args:
            cache_dir: Store the cache data in the provided directory.
            no_cache_dir: Disable the cache.
            no_deps: Don't install package dependencies.
            requirements: Path to a ``requirements.txt`` file.
            target: Path to a directory where dependencies will be installed.

        """
        return cls.generate_command(
            "install",
            cache_dir=str(cache_dir) if cache_dir else None,
            disable_pip_version_check=True,
            no_cache_dir=no_cache_dir,
            no_deps=no_deps,
            no_input=True,
            requirement=str(requirements),
            target=str(target),
        )

    def install(
        self,
        *,
        cache_dir: StrPath | None = None,
        extend_args: list[str] | None = None,
        no_cache_dir: bool = False,
        no_deps: bool = False,
        requirements: StrPath,
        target: StrPath,
    ) -> Path:
        """Install dependencies to a target directory.

        Args:
            cache_dir: Store the cache data in the provided directory.
            extend_args: Optional list of extra arguments to pass to ``pip install``.
                This value will not be parsed or sanitized in any way - it will
                be used as is. It is the user's responsibility to ensure that
                there are no overlapping arguments between this list and the
                arguments that are automatically generated.
            no_cache_dir: Disable the cache.
            no_deps: Don't install package dependencies.
            requirements: Path to a ``requirements.txt`` file.
            target: Path to a directory where dependencies will be installed.

        Raises:
            PipInstallFailedError: The subprocess used to run the commend
                exited with an error.

        """
        target = Path(target) if not isinstance(target, Path) else target
        target.mkdir(exist_ok=True, parents=True)
        try:
            self._run_command(
                self.generate_install_command(
                    cache_dir=cache_dir,
                    no_cache_dir=no_cache_dir,
                    no_deps=no_deps,
                    requirements=requirements,
                    target=target,
                )
                + (extend_args or []),
                suppress_output=False,
            )
        except subprocess.CalledProcessError as exc:
            raise PipInstallFailedError from exc
        return target

    @classmethod
    def generate_command(
        cls,
        command: list[str] | str,
        **kwargs: bool | Iterable[str] | str | None,
    ) -> list[str]:
        """Generate command to be executed and log it.

        Args:
            command: Command to run.
            args: Additional args to pass to the command.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            The full command to be passed into a subprocess.

        """
        cmd = [
            "python",
            "-m",
            cls.EXECUTABLE,
            *(command if isinstance(command, list) else [command]),
        ]
        cmd.extend(cls._generate_command_handle_kwargs(**kwargs))
        LOGGER.debug("generated command: %s", shlex_join(cmd))
        return cmd
