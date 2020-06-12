"""``runway tfenv`` command group."""
import click

from .install import install
from .run import run


__all__ = ['install', 'run']

COMMANDS = [install, run]


@click.group('tfenv', short_help='terraform (install|run)')
def tfenv():
    """Terraform version management and execution.

    Runway's built-in Terraform version management allows for long-term
    stability of Terraform executions. Define a ".terraform-version" file
    in your Terraform module and that version will be automatically
    downloaded & used during Runway operations.

    """


for cmd in COMMANDS:  # register commands
    tfenv.add_command(cmd)
