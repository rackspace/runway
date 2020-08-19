"""``runway deploy`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from ...core import Runway
from .. import options
from ..utils import select_deployments

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("deploy", short_help="deploy things")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def deploy(ctx, tags, **_):  # noqa: D301
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Deploy infrastructure as code.

    \b
    1. Determines the deploy environment.
        - option
        - "DEPLOY_ENVIRONMENT" environment variable
        - git branch name (strips "ENV-" prefix, master => common)
        - current working directory
    2. Selects deployments & modules to deploy.
        - (default) prompts
        - (tags) module contains all tags
        - (non-interactive) all
    3. Deploys selected in the order defined.

    """
    deployments = select_deployments(ctx, ctx.obj.runway_config.deployments, tags)
    Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).deploy(deployments)
