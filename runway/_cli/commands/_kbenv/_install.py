"""Install a version of kubectl."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import Any  # pylint: disable=W

import click

from ....env_mgr.kbenv import KBEnvManager
from ... import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("install", short_help="install kubectl")
@click.argument("version", metavar="[<version>]", required=False)
@options.debug
@options.no_color
@options.verbose
def install(version, **_):
    # type: (str, Any) -> None
    """Install the specified <version> of kubectl (e.g. v1.14.0).

    If no version is specified, Runway will attempt to find and read a
    ".kubectl-version" file in the current directory. If this file doesn't
    exist, nothing will be installed.

    Compatible with https://github.com/alexppg/kbenv.

    """
    LOGGER.debug("kubectl path: %s", KBEnvManager().install(version_requested=version))
