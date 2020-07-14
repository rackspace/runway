"""Install a version of Terraform."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import Any  # pylint: disable=W

import click

from ....env_mgr.tfenv import TFEnvManager
from ... import options

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('install', short_help='install terraform')
@click.argument('version', metavar='[<version>]', required=False, default=None)
@options.debug
@options.no_color
@options.verbose
def install(version, **_):
    # type: (str, Any) -> None
    """Install the specified <version> of Terraform (e.g. 0.12.0).

    If no version is specified, Runway will attempt to find and read a
    ".terraform-version" file in the current directory. If this file doesn't
    exist, nothing will be installed.

    """
    LOGGER.debug('terraform path: %s',
                 TFEnvManager().install(version_requested=version))
