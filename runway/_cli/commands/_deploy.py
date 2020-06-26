"""``runway deploy`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from ...core import Runway
from .. import options
from ..utils import select_deployments, select_modules_using_tags

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('deploy', short_help='deploy things')
@options.ci
@options.deploy_environment
@options.tags
@click.pass_context
def deploy(ctx, tags, **_):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Deploy infrastructure as code modules with Runway."""
    if tags:
        deployments = select_modules_using_tags(
            ctx, ctx.obj.runway_config.deployments, tags
        )
    elif ctx.obj.env.ci:
        deployments = ctx.obj.runway_config.deployments
    else:
        deployments = select_deployments(
            ctx, ctx.obj.runway_config.deployments
        )
    Runway(ctx.obj.runway_config,
           ctx.obj.get_runway_context()).deploy(deployments)
