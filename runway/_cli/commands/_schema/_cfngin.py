"""Output CFNgin configuration file schema."""

from __future__ import annotations

import json
import locale
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ....config.models.cfngin import CfnginConfigDefinitionModel
from ... import options

if TYPE_CHECKING:
    from runway._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


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
def cfngin(indent: int, output: str | None, **_: Any) -> None:
    """Output JSON schema for CFNgin configuration files.

    The schema that is output can be used to validate configuration files.
    It can also be added to text editors to provide autocompletion, tool tips,
    and suggestions within configuration files.

    """
    content = json.dumps(CfnginConfigDefinitionModel.model_json_schema(), indent=indent)
    if output:
        file_path = Path(output).absolute()
        file_path.write_text(  # append empty line to end of file
            content + "\n", encoding=locale.getpreferredencoding(do_setlocale=False)
        )
        LOGGER.success("output JSON schema to %s", file_path)
    else:
        click.echo(content)
