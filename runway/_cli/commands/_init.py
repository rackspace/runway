"""``runway init`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
import sys
from typing import Any  # pylint: disable=W

import click
import six

from .. import options

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace("._", "."))
RUNWAY_YML = """---
# See full syntax at https://docs.onica.com/projects/runway/en/latest/
deployments:
  - modules:
      - path: sampleapp.cfn
      - path: sampleapp.tf
      # - etc...
    regions:
      - us-east-1
"""


@click.command("init", short_help="create runway.yml")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def init(ctx, **_):
    # type: (click.Context, Any) -> None
    """Create an example runway.yml file in the currect directory."""
    runway_yml = Path.cwd() / "runway.yml"

    LOGGER.verbose("checking for preexisting runway.yml file...")
    if runway_yml.is_file():
        LOGGER.error(
            "There is already a %s file in the current directory", runway_yml.name
        )
        ctx.exit(1)

    # TODO remove use of six when dropping python 2
    runway_yml.write_text(six.u(RUNWAY_YML))
    LOGGER.success("runway.yml generated")
    LOGGER.notice(
        "See addition getting started information at "
        "https://docs.onica.com/projects/runway/en/latest/getting_started.html"
    )
