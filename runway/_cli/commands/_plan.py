"""``runway plan`` command."""

# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any

import click
from pydantic import ValidationError

from ...core import Runway
from ...exceptions import ConfigNotFound, VariablesFileNotFound
from .. import options
from ..changeset_output import output_changesets
from ..utils import select_deployments

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("plan", short_help="plan things")
@options.ci
@options.create_changeset
@options.changeset_output_format
@options.debug
@options.deploy_environment
@options.modules
@options.no_color
@options.stacks
@options.tags
@options.verbose
@click.pass_context
def plan(
    ctx: click.Context,
    create_changeset: bool,
    debug: bool,
    modules: tuple[str, ...],
    output_format: str,
    stacks: tuple[str, ...],
    tags: tuple[str, ...],
    **_: Any,
) -> None:
    """Determine what infrastructure changes will occur during the next deploy.

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
        - (--module) module name matches pattern
        - (--tag) module contains all tags
        - (non-interactive) all
    3. Attempt to determine change for deployments/modules in the order defined.

    \b
    Changeset Support (CI/CD)
    -------------------------
    Use --create-changeset to retain CloudFormation changesets for later execution:
        runway plan --create-changeset --output json > changesets.json
        runway deploy --execute-changesets changesets.json

    """  # noqa: D301
    try:
        # Store options in context for CFNgin to use
        ctx.obj.stacks = stacks
        ctx.obj.create_changeset = create_changeset
        ctx.obj.output_format = output_format

        runway_ctx = ctx.obj.get_runway_context()
        Runway(ctx.obj.runway_config, runway_ctx).plan(
            select_deployments(ctx, ctx.obj.runway_config.deployments, tags, modules)
        )

        # Output changeset information if --create-changeset was used
        if create_changeset:
            output_changesets(runway_ctx.changeset_results, output_format)

    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)
