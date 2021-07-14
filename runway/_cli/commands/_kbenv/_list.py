"""List the versions of kubectl that have been installed by Runway and/or kbenv."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import Any

import click

from ....env_mgr.kbenv import KBEnvManager
from ... import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("list", short_help="list installed versions")
@options.debug
@options.no_color
@options.verbose
def list_installed(**_: Any) -> None:
    """List the versions of kubectl that have been installed by Runway and/or kbenv."""
    kbenv = KBEnvManager()
    versions = list(kbenv.list_installed())
    versions.sort()

    if versions:
        LOGGER.info("kubectl versions installed:")
        click.echo("\n".join(v.name for v in versions))
    else:
        LOGGER.warning(
            "no versions of kubectl installed at path %s", kbenv.versions_dir
        )
