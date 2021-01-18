"""``runway kbenv`` command group."""
# docs: file://./../../../../docs/source/commands.rst
from typing import Any

import click

from ... import options
from ._install import install
from ._run import run

__all__ = ["install", "run"]

COMMANDS = [install, run]


@click.group("kbenv", short_help="kubectl (install|run)")
@options.debug
@options.no_color
@options.verbose
def kbenv(**_: Any) -> None:
    """kubectl version management and execution.

    Compatible with https://github.com/alexppg/kbenv.

    """


for cmd in COMMANDS:  # register commands
    kbenv.add_command(cmd)
