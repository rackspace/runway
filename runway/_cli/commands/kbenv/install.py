"""Install a version of kubectl."""
import logging

import click

from ....env_mgr.kbenv import KBEnvManager

LOGGER = logging.getLogger(__name__)


@click.command('install', short_help='install kubectl')
@click.argument('version', metavar='<version>', required=False)
def install(version):
    # type: (str) -> None
    """Install the specified <version> of kubectl (e.g. v1.14.0).

    If no version is specified, Runway will attempt to find and read a
    ".kubectl-version" file in the current directory. If this file doesn't
    exist, nothing will be installed.

    Compatible with https://github.com/alexppg/kbenv.

    """
    LOGGER.debug('kubectl path: %s',
                 KBEnvManager().install(version_requested=version))
