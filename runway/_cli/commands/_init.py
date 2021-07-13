"""``runway init`` command."""
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


@click.command("init", short_help="initialize/bootstrap things")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def init(ctx: click.Context, debug: bool, tags: Tuple[str, ...], **_: Any) -> None:
    """Run initialization/bootstrap steps.

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
    3. Initializes/bootstraps selected deployments/modules in the order defined.
       (e.g. "cdk bootstrap", "terraform init")

    \b
    Steps By Module Type
    --------------------
    - AWS CDK: Runs "cdk bootstrap".
    - CFNgin: Creates the "cfngin_bucket" if needed.
    - Terraform: Runs "terraform init", changes the workspace if needed, runs
      "terraform init" again if the workspace was changed, and finally
      downloads/updates Terraform modules.

    """  # noqa: D301
    try:
        Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).init(
            select_deployments(ctx, ctx.obj.runway_config.deployments, tags)
        )
    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)
