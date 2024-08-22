"""Poetry interface."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import tomli

from ..compat import cached_property
from ..exceptions import RunwayError
from ..utils import Version
from .base_classes import DependencyManager

if TYPE_CHECKING:
    from _typeshed import StrPath

LOGGER = logging.getLogger(__name__)


class PoetryExportFailedError(RunwayError):
    """Poetry export failed to produce a ``requirements.txt`` file."""

    def __init__(self, output: str, *args: Any, **kwargs: Any) -> None:
        """Instantiate class. All args/kwargs are passed to parent method.

        Args:
            output: The output from running ``poetry export``.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.message = f"poetry export failed with the following output:\n{output}"
        super().__init__(*args, **kwargs)


class PoetryNotFoundError(RunwayError):
    """Poetry not installed or found in $PATH."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class. All args/kwargs are passed to parent method."""
        self.message = (
            "poetry not installed or not in PATH! "
            "Install it according to poetry docs (https://python-poetry.org/) "
            "and ensure it is available in PATH."
        )
        super().__init__(*args, **kwargs)


class Poetry(DependencyManager):
    """Poetry dependency manager."""

    CONFIG_FILES: ClassVar[tuple[str, ...]] = (
        "poetry.lock",
        "pyproject.toml",
    )
    """Configuration files used by poetry."""

    EXECUTABLE: ClassVar[str] = "poetry"
    """CLI executable."""

    @cached_property
    def version(self) -> Version:
        """poetry version."""
        cmd_output = self._run_command([self.EXECUTABLE, "--version"])
        match = re.search(r"^Poetry version (?P<version>\S*)", cmd_output)
        if not match:
            LOGGER.warning("unable to parse poetry version from output:\n%s", cmd_output)
            return Version("0.0.0")
        return Version(match.group("version"))

    @classmethod
    def dir_is_project(cls, directory: StrPath, **__kwargs: Any) -> bool:
        """Determine if the directory contains a project for this dependency manager.

        Args:
            directory: Directory to check.

        """
        pyproject_path = Path(directory) / Poetry.CONFIG_FILES[1]

        if not pyproject_path.is_file():
            return False

        # check for PEP-517 definition
        pyproject = tomli.loads(pyproject_path.read_text())
        build_system_requires: list[str] | None = pyproject.get("build-system", {}).get("requires")

        if build_system_requires:
            for req in build_system_requires:
                if req.startswith("poetry"):
                    LOGGER.debug("poetry project detected")
                    return True
        return False

    def export(
        self,
        *,
        dev: bool = False,
        extras: list[str] | None = None,
        output: StrPath,
        output_format: str = "requirements.txt",
        with_credentials: bool = True,
        without_hashes: bool = True,
    ) -> Path:
        """Export the lock file to other formats.

        Args:
            dev: Include development dependencies.
            extras: Extra sets of dependencies to include.
            output: Path to the output file.
            output_format: The format to export to.
            with_credentials: Include credentials for extra indices.
            without_hashes: Exclude hashes from the exported file.

        Returns:
            Path to the output file.

        """
        output = Path(output)
        try:
            result = self._run_command(
                self.generate_command(
                    "export",
                    dev=dev,
                    extras=extras,
                    format=output_format,
                    output=output.name,
                    with_credentials=with_credentials,
                    without_hashes=without_hashes,
                )
            )
            requirements_txt = self.cwd / output.name
            if requirements_txt.is_file():
                output.parent.mkdir(exist_ok=True, parents=True)
                requirements_txt.rename(output)  # python3.7 doesn't return the new path
                return output
        except subprocess.CalledProcessError as exc:
            raise PoetryExportFailedError(exc.stderr) from exc
        raise PoetryExportFailedError(result)
