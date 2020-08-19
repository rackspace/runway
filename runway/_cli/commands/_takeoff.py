"""``runway takeoff`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any  # pylint: disable=W

import click

from .. import options
from ._deploy import deploy

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("takeoff", short_help="alias of deploy")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def takeoff(ctx, **kwargs):
    # type: (click.Context, Any) -> None
    """Alias of "runway deploy"."""
    LOGGER.verbose("forwarding to deploy...")
    ctx.forward(deploy, **kwargs)
