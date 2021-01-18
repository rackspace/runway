"""``runway gen-sample sls-tsc`` command."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("sls-tsc", short_help="sls + tsc (sampleapp.sls)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def sls_tsc(ctx: click.Context, **_: Any) -> None:
    """Generate a sample Serverless project using TypeScript."""
    src = TEMPLATES / "sls-tsc"
    dest = Path.cwd() / "sampleapp.sls"

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / "_gitignore")

    LOGGER.success("Sample Serverless module created at %s", dest)
    LOGGER.notice(
        "To finish it's setup, change to the %s directory and "
        'execute "npm install" to generate it\'s lockfile.',
        dest,
    )
