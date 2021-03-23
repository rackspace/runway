"""Output CFNgin configuration file schema."""
from pathlib import Path
from typing import Any, Optional

import click

from ....config.models.cfngin import CfnginConfigDefinitionModel
from ... import options


@click.command("cfngin", short_help="config schema")
@options.debug
@click.option(
    "--indent",
    default=4,
    help="Number of spaces to use per indentation level when output JSON.",
    metavar="<int>",
    show_default=True,
    type=click.INT,
)
@options.no_color
@click.option(
    "-o",
    "--output",
    default=None,
    help="If provided, schema will be saved to a file instead of being output to stdout.",
    metavar="<file-name>",
)
@options.verbose
def cfngin(indent: int, output: Optional[str], **_: Any) -> None:
    """Output CFNgin configuration file schema."""
    content = CfnginConfigDefinitionModel.schema_json(indent=indent)
    if output:
        Path(output).write_text(content + "\n")  # append empty line to end of file
    else:
        click.echo(content)
