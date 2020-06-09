"""Generate a sample AWS CDK project using C#."""
import logging
import sys

import click

from .utils import TEMPLATES, convert_gitignore, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


@click.command('cdk-csharp', short_help='cdk + c# (sampleapp.cdk)')
@click.pass_context
def cdk_csharp(ctx):
    # type: (click.Context) -> None
    """Generate a sample AWS CDK project using C#."""
    src = TEMPLATES / 'cdk-csharp'
    dest = Path.cwd() / 'sampleapp.cdk'

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / 'dot_gitignore')

    LOGGER.info("Sample C# CDK module created at %s", dest)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', dest)
