"""``runway deploy`` command."""

# docs: file://./../../../docs/source/commands.rst
from __future__ import annotations

import logging
from typing import Any

import click
from pydantic import ValidationError

from ...core import Runway
from ...exceptions import ConfigNotFound, VariablesFileNotFound
from .. import options
from ..changeset_executor import ChangesetExecutionError, execute_changesets_from_file
from ..utils import select_deployments

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("deploy", short_help="deploy things")
@options.ci
@options.debug
@options.deploy_environment
@options.execute_changesets
@options.modules
@options.no_color
@options.stacks
@options.tags
@options.verbose
@click.pass_context
def deploy(
    ctx: click.Context,
    changeset_file: str | None,
    debug: bool,
    modules: tuple[str, ...],
    stacks: tuple[str, ...],
    tags: tuple[str, ...],
    **_: Any,
) -> None:
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
        - (--module) module name matches pattern
        - (--tag) module contains all tags
        - (non-interactive) all
    3. Deploys selected deployments/modules in the order defined.

    \b
    Changeset Execution (CI/CD)
    ---------------------------
    Execute pre-created changesets instead of normal deploy:
        runway deploy --execute-changesets changesets.json

    The changesets.json file is created by:
        runway plan --create-changeset --output json > changesets.json

    """  # noqa: D301
    try:
        # Execute changesets from file if provided
        if changeset_file:
            runway_ctx = ctx.obj.get_runway_context()
            execute_changesets_from_file(runway_ctx, changeset_file, stack_filter=stacks or None)
            return

        # Normal deploy flow
        ctx.obj.stacks = stacks
        Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).deploy(
            select_deployments(ctx, ctx.obj.runway_config.deployments, tags, modules)
        )
    except ChangesetExecutionError as err:
        LOGGER.error(str(err), exc_info=debug)
        ctx.exit(1)
    except (FileNotFoundError, ValueError) as err:
        # Handle changeset file errors (not found, invalid JSON)
        LOGGER.error(str(err), exc_info=debug)
        ctx.exit(1)
    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)
