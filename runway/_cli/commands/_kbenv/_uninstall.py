"""Uninstall kubectl version(s) that were installed by Runway and/or kbenv."""
# docs: file://./../../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, Optional, cast

import click

from ....env_mgr.kbenv import KBEnvManager
from ... import options

if TYPE_CHECKING:
    from runway._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("uninstall", short_help="uninstall kubectl")
@click.argument("version", metavar="[<version>]", default=None, required=False)
@click.option(
    "--all",
    "all_versions",
    default=False,
    help="Uninstall all versions of kubectl.",
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
    """Uninstall the specified <version> of kubectl (e.g. v1.14.0) or all installed versions.

    If no version is specified, Runway will attempt to find and read a
    ".kubectl-version" file in the current directory.

    """
    kbenv = KBEnvManager()
    version = version or (str(kbenv.version) if kbenv.version else None)
    if version:
        version_tuple = KBEnvManager.parse_version_string(version)
    else:
        version_tuple = kbenv.version
    if version_tuple and not all_versions:
        if not kbenv.uninstall(version_tuple):
            ctx.exit(1)
        return
    if all_versions:
        LOGGER.notice("uninstalling all versions of kubectl...")
        for v in kbenv.list_installed():
            kbenv.uninstall(v.name)
        LOGGER.success("all versions of kubectl have been uninstalled")
        return
    LOGGER.error("version not specified")
    ctx.exit(1)
