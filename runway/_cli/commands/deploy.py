"""``runway deploy`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from .. import options
from ...core import Runway
from ...context import Context
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
    runway = Runway(ctx.obj.runway_config, Context(
        deploy_environment=ctx.obj.env))
    if tags:
        runway.deploy(select_modules_using_tags(
            ctx, ctx.obj.runway_config.deployments, tags
        ))
    elif ctx.obj.env.ci:
        runway.deploy()
    else:
        runway.deploy(select_deployments(
            ctx, ctx.obj.runway_config.deployments
        ))
