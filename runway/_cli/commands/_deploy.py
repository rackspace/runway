"""``runway deploy`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple

import click
from pydantic import ValidationError

from ...core import Runway
from ...exceptions import ConfigNotFound, VariablesFileNotFound
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
def deploy(ctx: click.Context, debug: bool, tags: Tuple[str, ...], **_: Any) -> None:
    """Deploy infrastructure as code.

    \b
    Process
    -------
    1. Determines the deploy environment.
        - "-e, --deploy-environment" option
        - "DEPLOY_ENVIRONMENT" environment variable
        - git branch name
            - strips "ENV-" prefix, master is converted to common
            - ignored if "ignore_git_branch: true"
        - name of the current working directory
    2. Selects deployments & modules to deploy.
        - (default) prompts
        - (tags) module contains all tags
        - (non-interactive) all
    3. Deploys selected deployments/modules in the order defined.

    """  # noqa: D301
    try:
        Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).deploy(
            select_deployments(ctx, ctx.obj.runway_config.deployments, tags)
        )
    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)
