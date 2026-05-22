"""Runway context."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, cast

from ..compat import cached_property
from ..core.components import DeployEnvironment
from ._base import BaseContext

if TYPE_CHECKING:
    from pathlib import Path

    from .._logging import PrefixAdaptor, RunwayLogger
    from ..core.type_defs import RunwayActionTypeDef

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def str2bool(v: str) -> bool:
    """Return boolean value of string."""
    return v.lower() in ("yes", "true", "t", "1", "on", "y")


class RunwayContext(BaseContext):
    """Runway context object."""

    changeset_results: dict[str, str]
    """Mapping of stack FQN to changeset ID for retained changesets."""

    command: RunwayActionTypeDef | None
    """Runway command/action being run."""

    create_changeset: bool
    """Whether to retain CloudFormation changesets instead of deleting them."""

    output_format: str
    """Output format for changeset information (text or json)."""

    stack_names: list[str]
    """CFNgin stack names to target. If empty, all stacks are targeted."""

    def __init__(
        self,
        *,
        command: RunwayActionTypeDef | None = None,
        create_changeset: bool = False,
        deploy_environment: DeployEnvironment | None = None,
        logger: PrefixAdaptor | RunwayLogger = LOGGER,
        output_format: str = "text",
        stack_names: list[str] | None = None,
        work_dir: Path | None = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            command: Runway command/action being run.
            create_changeset: Whether to retain changesets instead of deleting.
            deploy_environment: The current deploy environment.
            logger: Custom logger.
            output_format: Output format for changeset info (text or json).
            stack_names: CFNgin stack names to target. If not provided,
                all stacks defined in the config will be targeted.
            work_dir: Working directory used by Runway.

        """
        super().__init__(
            deploy_environment=deploy_environment or DeployEnvironment(),
            logger=logger,
            work_dir=work_dir,
        )
        self.changeset_results = {}
        self.command = command
        self.create_changeset = create_changeset
        self.output_format = output_format
        self.stack_names = stack_names or []
        self._inject_profile_credentials()

    @cached_property
    def no_color(self) -> bool:
        """Whether to explicitly disable color output.

        Primarily applies to IaC being wrapped by Runway.

        """
        colorize = self.env.vars.get("RUNWAY_COLORIZE")  # explicitly enable/disable
        try:
            if isinstance(colorize, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
                # catch False
                return not colorize
            if colorize and isinstance(colorize, str):  # type: ignore
                return not str2bool(colorize)
        except ValueError:
            pass  # likely invalid RUNWAY_COLORIZE value
        return not sys.stdout.isatty()

    @cached_property
    def use_concurrent(self) -> bool:
        """Whether to use concurrent.futures or not.

        Noninteractive is required for concurrent execution to prevent weird
        user-input behavior.

        Python 3 is required because backported futures has issues with
        ProcessPoolExecutor.

        """
        if self.is_noninteractive:
            if not self.sys_info.os.is_posix:
                LOGGER.warning(
                    "parallel execution disabled; only POSIX systems are supported currently"
                )
                return False
            return True
        LOGGER.warning("parallel execution disabled; not running in CI mode")
        return False

    def copy(self) -> RunwayContext:
        """Copy the contents of this object into a new instance."""
        return self.__class__(
            command=self.command,
            create_changeset=self.create_changeset,
            deploy_environment=self.env.copy(),
            logger=self.logger,
            output_format=self.output_format,
            stack_names=self.stack_names.copy(),
            work_dir=self.work_dir,
        )

    def echo_detected_environment(self) -> None:
        """Print a helper note about how the environment was determined."""
        self.env.log_name()
