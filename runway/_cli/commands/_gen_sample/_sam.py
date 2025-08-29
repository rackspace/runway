"""``runway gen-sample sam`` command."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import TEMPLATES, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("sam", short_help="AWS SAM (sampleapp.sam)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def sam(ctx: click.Context, **_: Any) -> None:
    """Generate a sample AWS SAM project."""
    src = TEMPLATES / "sam"
    dest = Path.cwd() / "sampleapp.sam"

    copy_sample(ctx, src, dest)
    LOGGER.success("Sample AWS SAM module created at %s", dest)
