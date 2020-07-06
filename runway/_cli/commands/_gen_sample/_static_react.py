"""``runway gen-sample static-react`` command."""
import logging
import sys

import click

from ... import options
from .utils import TEMPLATES, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('static-react',
               short_help='react static site (static-react)')
@options.debug
@options.verbose
@click.pass_context
def static_react(ctx):
    # type: (click.Context) -> None
    """Generate a sample static site project using React."""
    src = TEMPLATES / 'static-react'
    dest = Path.cwd() / 'static-react'

    copy_sample(ctx, src, dest)

    LOGGER.info("Sample static React site repo created at %s", dest)
    LOGGER.info('(see its README for setup and deployment instructions)')
