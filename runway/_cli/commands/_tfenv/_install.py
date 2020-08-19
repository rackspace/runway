"""Install a version of Terraform."""
# docs: file://./../../../../docs/source/commands.rst
import logging
import sys
from typing import Any  # pylint: disable=W

import click

from ....env_mgr.tfenv import TFEnvManager
from ....util import DOC_SITE
from ... import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("install", short_help="install terraform")
@click.argument("version", metavar="[<version>]", required=False, default=None)
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
    try:
        LOGGER.debug(
            "terraform path: %s", TFEnvManager().install(version_requested=version)
        )
    except ValueError as err:
        LOGGER.debug("terraform install failed", exc_info=True)
        if "unable to find" not in str(err):
            LOGGER.error(
                "unexpected error encountered when trying to install Terraform",
                exc_info=True,
            )
            sys.exit(1)
        else:
            LOGGER.error("unable to find a .terraform-version file")
            LOGGER.error(
                "learn how to use Runway to manage Terraform versions at "
                "%s/page/terraform/advanced_features.html#version-management",
                DOC_SITE,
            )
        sys.exit(1)
