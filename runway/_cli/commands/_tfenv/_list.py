"""List the versions of Terraform that have been installed by Runway and/or tfenv."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import Any

import click

from ....env_mgr.tfenv import TFEnvManager
from ... import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("list", short_help="list installed versions")
@options.debug
@options.no_color
@options.verbose
def list_installed(**_: Any) -> None:
    """List the versions of Terraform that have been installed by Runway and/or tfenv."""
    tfenv = TFEnvManager()
    versions = list(tfenv.list_installed())
    versions.sort()

    if versions:
        LOGGER.info("Terraform versions installed:")
        click.echo("\n".join(v.name for v in versions))
    else:
        LOGGER.warning(
            "no versions of Terraform installed at path %s", tfenv.versions_dir
        )
