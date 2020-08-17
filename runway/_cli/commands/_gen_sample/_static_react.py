"""``runway gen-sample static-react`` command."""
import logging
import sys
from typing import Any  # pylint: disable=W

import click

from ... import options
from .utils import TEMPLATES, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("static-react", short_help="react static site (static-react)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def static_react(ctx, **_):
    # type: (click.Context, Any) -> None
    """Generate a sample static site project using React."""
    src = TEMPLATES / "static-react"
    dest = Path.cwd() / "static-react"

    copy_sample(ctx, src, dest)

    LOGGER.success("Sample static React site repo created at %s", dest)
    LOGGER.notice("See the README for setup and deployment instructions.")
