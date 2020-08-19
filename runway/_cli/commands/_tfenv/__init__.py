"""``runway tfenv`` command group."""
# docs: file://./../../../../docs/source/commands.rst
from typing import Any  # pylint: disable=W

import click

from ... import options
from ._install import install
from ._run import run

__all__ = ["install", "run"]

COMMANDS = [install, run]


@click.group("tfenv", short_help="terraform (install|run)")
@options.debug
@options.no_color
@options.verbose
def tfenv(**_):
    # type: (Any) -> None
    """Terraform version management and execution.

    Runway's built-in Terraform version management allows for long-term
    stability of Terraform executions. Define a ".terraform-version" file
    in your Terraform module and that version will be automatically
    downloaded & used during Runway operations.

    """


for cmd in COMMANDS:  # register commands
    tfenv.add_command(cmd)
