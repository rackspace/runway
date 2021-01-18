"""``runway gen-sample static-react`` command."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import TEMPLATES, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("static-react", short_help="react static site (static-react)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def static_react(ctx: click.Context, **_: Any) -> None:
    """Generate a sample static site project using React."""
    src = TEMPLATES / "static-react"
    dest = Path.cwd() / "static-react"

    copy_sample(ctx, src, dest)

    LOGGER.success("Sample static React site repo created at %s", dest)
    LOGGER.notice("See the README for setup and deployment instructions.")
