"""Generate a sample AWS CDK project using TypeScript."""
import logging
import sys

import click

from .utils import TEMPLATES, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


@click.command('cdk-tsc', short_help='cdk + tsc (sampleapp.cdk)')
@click.pass_context
def cdk_tsc(ctx):
    # type: (click.Context) -> None
    """Generate a sample AWS CDK project using TypeScript."""
    src = TEMPLATES / 'cdk-tsc'
    dest = Path.cwd() / 'sampleapp.cdk'
    copy_sample(ctx, src, dest)
    # .gitignore already exists

    LOGGER.info("Sample CDK module created at %s", dest)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', dest)
