"""``runway tfenv`` command group."""
# docs: file://./../../../../docs/source/commands.rst
from typing import Any

import click

from ... import options
from ._install import install
from ._list import list_installed
from ._run import run
from ._uninstall import uninstall

__all__ = ["install", "list_installed", "run", "uninstall"]

COMMANDS = [install, list_installed, run, uninstall]


@click.group("tfenv", short_help="terraform (install|run)")
@options.debug
@options.no_color
@options.verbose
def tfenv(**_: Any) -> None:
    """Terraform version management and execution.

    Runway's built-in Terraform version management allows for long-term
    stability of Terraform executions. Define a ".terraform-version" file
    in your Terraform module and that version will be automatically
    downloaded & used during Runway operations.

    """


for cmd in COMMANDS:  # register commands
    tfenv.add_command(cmd)
