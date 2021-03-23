"""``runway schema`` command group."""
from typing import Any

import click

from ... import options
from ._cfngin import cfngin
from ._runway import runway

COMMANDS = [cfngin, runway]


@click.group("schema", short_help="JSON schema")
@options.debug
@options.no_color
@options.verbose
def schema(**_: Any) -> None:
    """Output JSON schema for Runway or CFNgin configuration files."""


for cmd in COMMANDS:  # register commands
    schema.add_command(cmd)
