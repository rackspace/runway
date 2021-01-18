"""Cloudformation module."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from .._logging import PrefixAdaptor
from ..cfngin.cfngin import CFNgin
from . import RunwayModule

if TYPE_CHECKING:
    from ..context import Context

LOGGER = logging.getLogger(__name__)


class CloudFormation(RunwayModule):
    """CloudFormation (Stacker) Runway Module."""

    def __init__(
        self,
        context: Context,
        path: Path,
        options: Optional[Dict[str, Union[Dict[str, Any], str]]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.
            path: Path to the module.
            options: Everything in the module definition merged with applicable
                values from the deployment definition.

        """
        super().__init__(context, path, options)
        self._raw_path = (
            Path(cast(str, options.pop("path"))) if options.get("path") else None
        )
        self.path = path if isinstance(self.path, Path) else Path(self.path)
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    def deploy(self) -> None:
        """Run stacker build."""
        cfngin = CFNgin(
            self.context,
            parameters=cast(Dict[str, Any], self.options["parameters"]),
            sys_path=self.path,
        )
        cfngin.deploy(
            force=bool(self.options["parameters"] or self.options["environment"])
        )

    def destroy(self) -> None:
        """Run stacker destroy."""
        cfngin = CFNgin(
            self.context,
            parameters=cast(Dict[str, Any], self.options["parameters"]),
            sys_path=self.path,
        )
        cfngin.destroy(
            force=bool(self.options["parameters"] or self.options["environment"])
        )

    def plan(self) -> None:
        """Run stacker diff."""
        cfngin = CFNgin(
            self.context,
            parameters=cast(Dict[str, Any], self.options["parameters"]),
            sys_path=self.path,
        )
        cfngin.plan(
            force=bool(self.options["parameters"] or self.options["environment"])
        )
