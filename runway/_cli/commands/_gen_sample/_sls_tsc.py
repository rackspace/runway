"""Generate a sample Serverless project using TypeScript."""
import logging
import sys

import click

from .utils import TEMPLATES, convert_gitignore, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('sls-tsc', short_help='sls + tsc (sampleapp.sls)')
@click.pass_context
def sls_tsc(ctx):
    """Generate a sample Serverless project using TypeScript."""
    src = TEMPLATES / 'sls-tsc'
    dest = Path.cwd() / 'sampleapp.sls'

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / '_gitignore')

    LOGGER.info("Sample Serverless module created at %s", dest)
    LOGGER.info('To finish it\'s setup, change to the %s directory and execute'
                ' "npm install" to generate it\'s lockfile.', dest)
