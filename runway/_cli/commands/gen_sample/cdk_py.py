"""Generate a sample AWS CDK project using python."""
import logging
import sys

import click

from .utils import TEMPLATES, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


@click.command('cdk-py', short_help='cdk + py (sampleapp.cdk)')
@click.pass_context
def cdk_py(ctx):
    # type: (click.Context) -> None
    """Generate a sample AWS CDK project using python."""
    src = TEMPLATES / 'cdk-py'
    dest = Path.cwd() / 'sampleapp.cdk'
    copy_sample(ctx, src, dest)
    # .gitignore already exists

    LOGGER.info("Sample CDK module created at %s", dest)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', dest)
