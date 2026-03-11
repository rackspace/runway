"""``runway variables`` command."""

# docs: file://./../../../docs/source/commands.rst
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, cast

import click
import yaml
from pydantic import ValidationError

from ...core import Runway, components
from ...exceptions import ConfigNotFound, UnresolvedVariable, VariablesFileNotFound
from .. import options
from ..utils import select_deployments

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("variables", short_help="show resolved variables")
@options.ci
@options.debug
@options.deploy_environment
@options.modules
@options.no_color
@options.tags
@options.verbose
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json", "table"]),
    default="yaml",
    help="Output format for variables (default: yaml).",
)
@click.pass_context
def variables(
    ctx: click.Context,
    debug: bool,
    modules: tuple[str, ...],
    output_format: str,
    tags: tuple[str, ...],
    **_: Any,
) -> None:
    """Show resolved variables that will be applied for a Runway run.

    This command displays all variables, parameters, and environment variables
    that would be applied when running Runway commands. It resolves all lookups
    (${var}, ${env}, ${ssm}, etc.) and shows the final values.

    \b
    Output includes:
    - Runway variables (from runway.variables.yml or inline)
    - Deployment-level parameters and env_vars
    - Module-level parameters and env_vars

    \b
    Examples:
        runway variables                    # Show all variables
        runway variables --module vpc.cfn   # Show variables for specific module
        runway variables --format json      # Output as JSON
        runway variables -e prod            # Show variables for prod environment

    """  # noqa: D301
    if not (ctx.obj.debug or ctx.obj.verbose):
        logging.getLogger("runway").setLevel(logging.ERROR)  # suppress warnings

    ctx.obj.env.ci = True
    LOGGER.verbose("forced Runway to non-interactive mode to suppress prompts")

    try:
        runway = Runway(ctx.obj.runway_config, ctx.obj.get_runway_context())
        deployments = select_deployments(ctx, ctx.obj.runway_config.deployments, tags, modules)
        result = get_resolved_variables(runway, deployments)
    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)

    if not result:
        LOGGER.warning("No variables found in configuration")
        ctx.exit(0)

    _print_variables(result, output_format)


def get_resolved_variables(
    runway: Runway,
    deployments: list[Any],
) -> dict[str, Any]:
    """Get all resolved variables for the given deployments.

    Args:
        runway: Runway instance.
        deployments: List of deployment definitions.

    Returns:
        Dictionary containing all resolved variables organized by scope.

    """
    result: dict[str, Any] = {
        "runway_variables": {},
        "deployments": [],
    }

    # Get runway-level variables
    if runway.variables:
        result["runway_variables"] = dict(runway.variables)

    # Get deployment and module variables
    for deployment_def in deployments:
        deployment_obj = components.Deployment(
            context=runway.ctx,
            definition=deployment_def,
            variables=runway.variables,
        )

        deployment_data: dict[str, Any] = {
            "name": deployment_def.name,
            "parameters": {},
            "env_vars": {},
            "modules": [],
        }

        # Resolve deployment parameters
        try:
            deployment_def.resolve(runway.ctx, variables=runway.variables)
            deployment_data["parameters"] = _safe_get_value(deployment_def, "parameters", {})
            deployment_data["env_vars"] = deployment_obj.env_vars_config
        except UnresolvedVariable as err:
            LOGGER.warning(
                "Could not resolve variable %s in deployment %s: %s",
                err.variable.name,
                deployment_def.name,
                err,
            )
            deployment_data["parameters"] = {"_error": str(err)}

        # Get module variables
        for module_def in deployment_def.modules:
            module_data: dict[str, Any] = {
                "name": module_def.name,
                "path": str(module_def.path) if module_def.path else None,
                "parameters": {},
                "env_vars": {},
                "options": {},
            }

            try:
                module_def.resolve(runway.ctx, variables=runway.variables)
                module_data["parameters"] = _safe_get_value(module_def, "parameters", {})
                module_data["env_vars"] = _safe_get_value(module_def, "env_vars", {})
                module_data["options"] = _safe_get_value(module_def, "options", {})
            except UnresolvedVariable as err:
                LOGGER.warning(
                    "Could not resolve variable %s in module %s: %s",
                    err.variable.name,
                    module_def.name,
                    err,
                )
                module_data["parameters"] = {"_error": str(err)}

            deployment_data["modules"].append(module_data)

        result["deployments"].append(deployment_data)

    return result


def _safe_get_value(obj: Any, attr: str, default: Any) -> Any:
    """Safely get an attribute value, returning default on error."""
    try:
        value = getattr(obj, attr, default)
        if value is None:
            return default
        # Convert to dict if it's a special type
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "__dict__") and not isinstance(value, (dict, list, str)):
            return dict(value)
        return value
    except (UnresolvedVariable, AttributeError):
        return default


def _print_variables(variables: dict[str, Any], output_format: str) -> None:
    """Print variables in the specified format.

    Args:
        variables: The resolved variables dictionary.
        output_format: Output format (yaml, json, or table).

    """
    if output_format == "json":
        click.echo(json.dumps(variables, indent=2, default=str))
    elif output_format == "table":
        _print_table(variables)
    else:  # yaml
        click.echo(yaml.safe_dump(variables, default_flow_style=False, sort_keys=False))


def _print_key_values(data: dict[str, Any], indent: str, show_none: bool = True) -> None:
    """Print key-value pairs with consistent formatting.

    Args:
        data: Dictionary of key-value pairs to print.
        indent: Indentation string for formatting.
        show_none: Whether to show (none) when data is empty.

    """
    if data:
        for key, value in data.items():
            click.echo(f"{indent}{key}: {value}")
    elif show_none:
        click.echo(f"{indent}(none)")


def _print_section(title: str, data: dict[str, Any], indent: str) -> None:
    """Print a section header and its key-value content.

    Args:
        title: Section title to display.
        data: Dictionary of key-value pairs.
        indent: Base indentation string.

    """
    click.secho(f"\n{indent}{title}:", bold=True)
    _print_key_values(data, indent + "  ")


def _print_module(module: dict[str, Any]) -> None:
    """Print module details in table format.

    Args:
        module: Module dictionary containing name, path, parameters, etc.

    """
    click.secho(f"\n  --- Module: {module['name']} ---", bold=True)
    if module.get("path"):
        click.echo(f"      Path: {module['path']}")

    if module.get("parameters"):
        click.secho("      Parameters:", bold=True)
        _print_key_values(module["parameters"], "        ", show_none=False)

    if module.get("env_vars"):
        click.secho("      Environment Variables:", bold=True)
        _print_key_values(module["env_vars"], "        ", show_none=False)

    if module.get("options"):
        click.secho("      Options:", bold=True)
        _print_key_values(module["options"], "        ", show_none=False)


def _print_table(variables: dict[str, Any]) -> None:
    """Print variables in a table format.

    Args:
        variables: The resolved variables dictionary.

    """
    click.secho("\n=== Runway Variables ===", bold=True)
    _print_key_values(variables.get("runway_variables", {}), "  ")

    for deployment in variables.get("deployments", []):
        click.secho(f"\n=== Deployment: {deployment['name']} ===", bold=True)
        _print_section("Parameters", deployment.get("parameters", {}), "  ")
        _print_section("Environment Variables", deployment.get("env_vars", {}), "  ")

        for module in deployment.get("modules", []):
            _print_module(module)

    click.echo()
