"""Install a version of Terraform."""
import logging

import click

from ....env_mgr.tfenv import TFEnvManager

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('install', short_help='install terraform')
@click.argument('version', metavar='[<version>]', required=False, default=None)
def install(version):
    # type: (str) -> None
    """Install the specified <version> of Terraform (e.g. 0.12.0).

    If no version is specified, Runway will attempt to find and read a
    ".terraform-version" file in the current directory. If this file doesn't
    exist, nothing will be installed.

    """
    LOGGER.debug('terraform path: %s',
                 TFEnvManager().install(version_requested=version))
