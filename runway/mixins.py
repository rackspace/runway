"""Class mixins."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from collections.abc import Iterable
from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, cast, overload

from .compat import shlex_join

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import Literal

    from ._logging import RunwayLogger
    from .context import CfnginContext, RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class CliInterfaceMixin:
    """Mixin for adding CLI interface methods."""

    EXECUTABLE: ClassVar[str]
    """CLI executable."""

    ctx: CfnginContext | RunwayContext
    """CFNgin or Runway context object."""

    cwd: Path
    """Working directory where commands will be run."""

    @staticmethod
    def convert_to_cli_arg(arg_name: str, *, prefix: str = "--") -> str:
        """Convert string kwarg name into a CLI argument."""
        return f"{prefix}{arg_name.replace('_', '-')}"

    @classmethod
    def found_in_path(cls) -> bool:
        """Determine if executable is found in $PATH."""
        return bool(shutil.which(cls.EXECUTABLE))

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
        cmd = [cls.EXECUTABLE, *(command if isinstance(command, list) else [command])]
        cmd.extend(cls._generate_command_handle_kwargs(**kwargs))
        LOGGER.debug("generated command: %s", cls.list2cmdline(cmd))
        return cmd

    @classmethod
    def _generate_command_handle_kwargs(
        cls, **kwargs: bool | Iterable[str] | str | None
    ) -> list[str]:
        """Handle kwargs passed to generate_command."""
        result: list[str] = []
        for k, v in kwargs.items():
            if isinstance(v, str):
                result.extend([cls.convert_to_cli_arg(k), v])
            elif isinstance(v, (list, set, tuple)):
                for i in cast(Iterable[str], v):
                    result.extend([cls.convert_to_cli_arg(k), i])
            elif isinstance(v, bool) and v:
                result.append(cls.convert_to_cli_arg(k))
        return result

    @staticmethod
    def list2cmdline(split_command: Iterable[str]) -> str:
        """Combine a list of strings into a string that can be run as a command.

        Handles multi-platform differences.

        """
        if platform.system() == "Windows":
            return subprocess.list2cmdline(split_command)
        return shlex_join(split_command)

    @overload
    def _run_command(
        self,
        command: Iterable[str] | str,
        *,
        env: dict[str, str] | None = ...,
        suppress_output: Literal[True] = ...,
    ) -> str: ...

    @overload
    def _run_command(
        self,
        command: Iterable[str] | str,
        *,
        env: dict[str, str] | None = ...,
        suppress_output: Literal[False] = ...,
    ) -> None: ...

    def _run_command(
        self,
        command: Iterable[str] | str,
        *,
        env: dict[str, str] | None = None,
        suppress_output: bool = True,
    ) -> str | None:
        """Run command.

        Args:
            command: Command to pass to shell to execute.
            env: Environment variables.
            suppress_output: If ``True``, the output of the subprocess written
                to ``sys.stdout`` and ``sys.stderr`` will be captured and
                returned as a string instead of being being written directly.

        """
        cmd_str = command if isinstance(command, str) else self.list2cmdline(command)
        LOGGER.verbose("running command: %s", cmd_str)
        if suppress_output:
            return subprocess.check_output(
                cmd_str,
                cwd=self.cwd,
                env=env or self.ctx.env.vars,
                shell=True,
                stderr=subprocess.PIPE,
                text=True,
            )
        subprocess.check_call(
            cmd_str,
            cwd=self.cwd,
            env=env or self.ctx.env.vars,
            shell=True,
        )
        return None


class DelCachedPropMixin:
    """Mixin to handle safely clearing the value of :func:`functools.cached_property`."""

    def _del_cached_property(self, *names: str) -> None:
        """Delete the cached value of a :func:`functools.cached_property`.

        Args:
            names: Names of the attribute that is cached. Can provide one or multiple.

        """
        for name in names:
            with suppress(AttributeError):
                delattr(self, name)
