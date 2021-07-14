"""Uninstall Terraform version(s) that were installed by Runway and/or tfenv."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, Optional, cast

import click

from ....env_mgr.tfenv import TFEnvManager
from ... import options

if TYPE_CHECKING:
    from runway._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("uninstall", short_help="uninstall terraform")
@click.argument("version", metavar="[<version>]", default=None, required=False)
@click.option(
    "--all",
    "all_versions",
    default=False,
    help="Uninstall all versions of Terraform.",
    is_flag=True,
    required=False,
    show_default=True,
)
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def uninstall(
    ctx: click.Context,
    *,
    version: Optional[str] = None,
    all_versions: bool = False,
    **_: Any,
) -> None:
    """Uninstall the specified <version> of Terraform (e.g. 0.12.0) or all installed versions.

    If no version is specified, Runway will attempt to find and read a
    ".terraform-version" file in the current directory.

    """
    tfenv = TFEnvManager()
    version = version or (str(tfenv.version) if tfenv.version else None)
    if version and not all_versions:
        if not tfenv.uninstall(version):
            ctx.exit(1)
        return
    if all_versions:
        LOGGER.notice("uninstalling all versions of Terraform...")
        for v in tfenv.list_installed():
            tfenv.uninstall(v.name)
        LOGGER.success("all versions of Terraform have been uninstalled")
        return
    LOGGER.error("version not specified")
    ctx.exit(1)
