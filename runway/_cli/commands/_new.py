"""``runway new`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))
RUNWAY_YML = """---
# See full syntax at https://docs.onica.com/projects/runway
deployments:
  - modules:
      - path: sampleapp.cfn
      - path: sampleapp.tf
      # - etc...
    regions:
      - us-east-1
"""


@click.command("new", short_help="create runway.yml")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def new(ctx: click.Context, **_: Any) -> None:
    """Create an example runway.yml file in the currect directory."""
    runway_yml = Path.cwd() / "runway.yml"

    LOGGER.verbose("checking for preexisting runway.yml file...")
    if runway_yml.is_file():
        LOGGER.error(
            "There is already a %s file in the current directory", runway_yml.name
        )
        ctx.exit(1)

    runway_yml.write_text(RUNWAY_YML)
    LOGGER.success("runway.yml generated")
    LOGGER.notice(
        "See addition getting started information at "
        "https://docs.onica.com/projects/runway/page/getting_started.html"
    )
