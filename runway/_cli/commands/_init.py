"""``runway init`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("init", short_help="coming soon")
@options.debug
@options.no_color
@options.verbose
def init(**_: Any) -> None:
    """Coming soon."""
    LOGGER.warning("functionality comming soon")
