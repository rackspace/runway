"""Cloudformation module."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from .._logging import PrefixAdaptor
from ..cfngin.cfngin import CFNgin
from .base import RunwayModule

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext
    from .base import ModuleOptions

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class CloudFormation(RunwayModule):
    """CloudFormation (CFNgin) Runway Module."""

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=options,
            parameters=parameters,
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    def deploy(self) -> None:
        """Run deploy."""
        cfngin = CFNgin(self.ctx, parameters=self.parameters, sys_path=self.path)
        cfngin.init(force=bool(self.parameters or self.explicitly_enabled))
        cfngin.deploy(force=bool(self.parameters or self.explicitly_enabled))

    def destroy(self) -> None:
        """Run destroy."""
        cfngin = CFNgin(self.ctx, parameters=self.parameters, sys_path=self.path)
        cfngin.destroy(force=bool(self.parameters or self.explicitly_enabled))

    def init(self) -> None:
        """Run init."""
        cfngin = CFNgin(self.ctx, parameters=self.parameters, sys_path=self.path)
        cfngin.init(force=bool(self.parameters or self.explicitly_enabled))

    def plan(self) -> None:
        """Run diff."""
        cfngin = CFNgin(self.ctx, parameters=self.parameters, sys_path=self.path)
        cfngin.plan(force=bool(self.parameters or self.explicitly_enabled))
