"""``runway destroy`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from ...core import Runway
from .. import options
from ..utils import select_deployments, select_modules_using_tags

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('destroy', short_help='destroy things')
@options.ci
@options.deploy_environment
@options.tags
@click.pass_context
def destroy(ctx, tags, **_):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Destroy infrastructure as code modules with Runway."""
    if not ctx.obj.env.ci:
        click.secho('[WARNING] Runway is about to be run in DESTROY mode. '
                    '[WARNING]', bold=True, fg='red')
        click.secho('Any/all deployment(s) selected will be irrecoverably '
                    'DESTROYED.', bold=True, fg='red')
        if not click.confirm('\nProceed?'):
            ctx.exit(0)
        click.echo('')

    if tags:
        deployments = Runway.reverse_deployments(select_modules_using_tags(
            ctx, ctx.obj.runway_config.deployments, tags
        ))
    elif ctx.obj.env.ci:
        deployments = Runway.reverse_deployments(
            ctx.obj.runway_config.deployments
        )
    else:
        deployments = Runway.reverse_deployments(select_deployments(
            ctx, ctx.obj.runway_config.deployments
        ))
    Runway(ctx.obj.runway_config,
           ctx.obj.get_runway_context()).destroy(deployments)
