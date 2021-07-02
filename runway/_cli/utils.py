"""CLI utils."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

import click
import yaml

from ..compat import cached_property
from ..config import RunwayConfig
from ..config.components.runway import (
    RunwayDeploymentDefinition,
    RunwayModuleDefinition,
)
from ..context import RunwayContext
from ..core.components import DeployEnvironment
from ..exceptions import ConfigNotFound

LOGGER = logging.getLogger(__name__)


class CliContext:
    """CLI context object."""

    def __init__(
        self,
        *,
        ci: bool = False,
        debug: int = 0,
        deploy_environment: Optional[str] = None,
        verbose: bool = False,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            ci: Whether Runway is being run in non-interactive mode.
            debug: Debug level
            deploy_environment: Name of the deploy environment.
            verbose: Whether to display verbose logs.

        """
        self._deploy_environment = deploy_environment
        self.ci = ci
        self.debug = debug
        self.root_dir = Path.cwd()
        self.verbose = verbose

    @cached_property
    def env(self) -> DeployEnvironment:
        """Name of the current deploy environment."""
        environ = os.environ.copy()
        # carefully update environ with values passed from the cli
        if self.ci and "CI" not in environ:
            environ["CI"] = "1"
        if self.debug and "DEBUG" not in environ:
            environ["DEBUG"] = str(self.debug)
        if self.verbose and "VERBOSE" not in environ:
            environ["VERBOSE"] = "1"
        return DeployEnvironment(
            environ=environ,
            explicit_name=self._deploy_environment,
            root_dir=self.root_dir,
        )

    @cached_property
    def runway_config(self) -> RunwayConfig:
        """Runway config."""
        config = RunwayConfig.parse_file(file_path=self.runway_config_path)
        self.env.ignore_git_branch = config.ignore_git_branch
        # self.env.root_dir = self.runway_config_path.parent
        return config

    @cached_property
    def runway_config_path(self) -> Path:
        """Path to the runway config file.

        Raises:
            SystemExit: Config file not found or multiple were matches were found.

        """
        try:
            path = RunwayConfig.find_config_file(self.root_dir)
            self.root_dir = path.parent
            self.env.root_dir = self.root_dir
            return path
        except ConfigNotFound as err:
            LOGGER.error(err.message)
        except ValueError as err:
            LOGGER.error(err)
        sys.exit(1)

    def get_runway_context(
        self, deploy_environment: Optional[DeployEnvironment] = None
    ) -> RunwayContext:
        """Get a Runway context object.

        Args:
            deploy_environment: Object representing the current deploy environment.

        Returns
            RunwayContext

        """
        return RunwayContext(deploy_environment=deploy_environment or self.env)

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            Attribute: If attribute does not exist on this object.

        """
        # ignore coverage for standard implimentation
        return getattr(self, key)  # cov: ignore

    def __setitem__(self, key: str, value: Any) -> None:
        """Implement assignment to self[key].

        Args:
            key: Attribute name to associate with a value.
            value: Value of a key/attribute.

        """
        # ignore coverage for standard implimentation
        setattr(self, key, value)  # cov: ignore

    def __delitem__(self, key: str) -> None:
        """Implement deletion of self[key].

        Args:
            key: Attribute name to remove from the object.

        """
        # ignore coverage for standard implimentation
        delattr(self, key)  # cov: ignore

    def __len__(self) -> int:
        """Implement the built-in function len()."""
        # ignore coverage for standard implimentation
        return len(self.__dict__)  # cov: ignore

    def __iter__(self) -> Iterator[str]:
        """Return iterator object that can iterate over all attributes."""
        # ignore coverage for standard implimentation
        return iter(self.__dict__)  # cov: ignore

    def __str__(self) -> str:
        """Return string representation of the object."""
        # ignore coverage for standard implimentation
        return f"CliContext({self.__dict__})"  # cov: ignore


def select_deployments(
    ctx: click.Context,
    deployments: List[RunwayDeploymentDefinition],
    tags: Optional[Tuple[str, ...]] = None,
) -> List[RunwayDeploymentDefinition]:
    """Select which deployments to run.

    Uses tags, interactive prompts, or selects all.

    Args:
        ctx: Current click context.
        deployments: List of deployment(s) to choose from.

    Returns:
        Selected deployment(s).

    """
    if tags:
        return select_modules_using_tags(ctx, deployments, tags)
    if ctx.obj.env.ci:
        return deployments
    if len(deployments) == 1:
        choice = 1
        LOGGER.debug("only one deployment detected; no selection necessary")
    else:
        # build the menu before displaying it so debug logs don't break up what is printed
        deployment_menu = yaml.safe_dump(
            {i + 1: d.menu_entry for i, d in enumerate(deployments)}
        )
        click.secho("\nConfigured deployments\n", bold=True, underline=True)
        click.echo(deployment_menu)
        if ctx.command.name == "destroy":
            click.echo(
                '(operating in destroy mode -- "all" will destroy all '
                "deployments in reverse order)\n"
            )
        choice = click.prompt(
            'Enter number of deployment to run (or "all")',
            default="all",
            show_choices=False,
            type=click.Choice(
                [str(n) for n in range(1, len(deployments) + 1)] + ["all"]
            ),
        )
    if choice != "all":
        deployments = [deployments[int(choice) - 1]]
        deployments[0].modules = select_modules(ctx, deployments[0].modules)
    return deployments


def select_modules(
    ctx: click.Context, modules: List[RunwayModuleDefinition]
) -> List[RunwayModuleDefinition]:
    """Interactively select which modules to run.

    Args:
        ctx: Current click context.
        modules: List of module(s) to choose from.

    Returns:
        Selected module(s).

    """
    if len(modules) == 1:
        LOGGER.debug("only one module detected; no selection necessary")
        if ctx.command.name == "destroy":
            LOGGER.info(
                "Only one module detected; all modules "
                "automatically selected for deletion."
            )
            if not click.confirm("Proceed?"):
                ctx.exit(0)
        return modules
    click.secho("\nConfigured modules\n", bold=True, underline=True)
    click.echo(yaml.safe_dump({i + 1: m.menu_entry for i, m in enumerate(modules)}))
    if ctx.command.name == "destroy":
        click.echo(
            '(operating in destroy mode -- "all" will destroy all '
            "modules in reverse order)\n"
        )
    choice = click.prompt(
        'Enter number of module to run (or "all")',
        default="all",
        show_choices=False,
        type=click.Choice([str(n) for n in range(1, len(modules) + 1)] + ["all"]),
    )
    click.echo("")
    if choice == "all":
        return modules
    modules = [modules[int(choice) - 1]]
    if modules[0].child_modules:
        return select_modules(ctx, modules[0].child_modules)
    return modules


def select_modules_using_tags(
    ctx: click.Context,
    deployments: List[RunwayDeploymentDefinition],
    tags: Tuple[str, ...],
) -> List[RunwayDeploymentDefinition]:
    """Select modules to run using tags.

    Args:
        ctx: Current click context.
        deployments: List of deployments to check.
        tags: List of tags to filter modules.

    Returns:
        List of selected deployments with selected modules.

    """
    deployments_to_run: List[RunwayDeploymentDefinition] = []
    for deployment in deployments:
        modules_to_run: List[RunwayModuleDefinition] = []
        for module in deployment.modules:
            if module.child_modules:
                module.child_modules = [
                    c for c in module.child_modules if all(t in c.tags for t in tags)
                ]
                if module.child_modules:
                    modules_to_run.append(module)
            elif all(t in module.tags for t in tags):
                modules_to_run.append(module)
        if modules_to_run:
            deployment.modules = modules_to_run
            deployments_to_run.append(deployment)
    if deployments_to_run:
        return deployments_to_run
    LOGGER.error("No modules found with the provided tag(s): %s", ", ".join(tags))
    return ctx.exit(1)
