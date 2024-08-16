"""Pipenv interface."""

from __future__ import annotations

import locale
import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from ..compat import cached_property
from ..exceptions import RunwayError
from ..utils import Version
from .base_classes import DependencyManager

if TYPE_CHECKING:
    from _typeshed import StrPath

LOGGER = logging.getLogger(__name__)


class PipenvExportFailedError(RunwayError):
    """Pipenv export failed to produce a ``requirements.txt`` file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class. All args/kwargs are passed to parent method."""
        self.message = (
            "pipenv lock to requirements.txt format failed; review pipenv's"
            " output above to troubleshoot"
        )
        super().__init__(*args, **kwargs)


class PipenvNotFoundError(RunwayError):
    """Pipenv not installed or found in $PATH."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class. All args/kwargs are passed to parent method."""
        self.message = (
            "pipenv not installed or not in PATH! "
            "Install it according to pipenv docs (https://pipenv.pypa.io/en/latest/) "
            "and ensure it is available in PATH."
        )
        super().__init__(*args, **kwargs)


class Pipenv(DependencyManager):
    """Pipenv dependency manager."""

    CONFIG_FILES: ClassVar[tuple[str, ...]] = (
        "Pipfile",
        "Pipfile.lock",
    )
    """Configuration files used by pipenv."""

    EXECUTABLE: ClassVar[str] = "pipenv"
    """CLI executable."""

    @cached_property
    def version(self) -> Version:
        """pipenv version."""
        cmd_output = self._run_command([self.EXECUTABLE, "--version"])
        match = re.search(r"^pipenv, version (?P<version>\S*)", cmd_output)
        if not match:
            LOGGER.warning("unable to parse pipenv version from output:\n%s", cmd_output)
            return Version("0.0.0")
        return Version(match.group("version"))

    @classmethod
    def dir_is_project(cls, directory: StrPath, **__kwargs: Any) -> bool:
        """Determine if the directory contains a project for this dependency manager.

        Args:
            directory: Directory to check.

        """
        dir_path = Path(directory)
        if not (dir_path / Pipenv.CONFIG_FILES[0]).is_file():
            return False

        if not (dir_path / Pipenv.CONFIG_FILES[1]).is_file():
            LOGGER.warning("%s not found", Pipenv.CONFIG_FILES[1])
        return True

    def export(self, *, dev: bool = False, output: StrPath) -> Path:
        """Export the lock file to other formats (requirements.txt only).

        The underlying command being executed by this method is
        ``pipenv lock --requirements``.

        Args:
            dev: Include development dependencies.
            output: Path to the output file.

        """
        output = Path(output)
        try:
            result = self._run_command(
                self.generate_command(
                    "lock",
                    dev=dev,
                    requirements=True,
                ),
                suppress_output=True,
            )
        except subprocess.CalledProcessError as exc:
            raise PipenvExportFailedError from exc
        output.parent.mkdir(exist_ok=True, parents=True)  # ensure directory exists
        output.write_text(str(result), encoding=locale.getpreferredencoding(do_setlocale=False))
        return output
