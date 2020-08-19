"""``runway plan`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from ...core import Runway
from .. import options
from ..utils import select_deployments

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("plan", short_help="plan things")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def plan(ctx, tags, **_):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Determine what infrastructure changes will occur during the next deploy."""
    deployments = select_deployments(ctx, ctx.obj.runway_config.deployments, tags)
    Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).plan(deployments)
