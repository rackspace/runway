"""``runway gen-sample tf`` command."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ....env_mgr.tfenv import get_latest_tf_version
from ... import options
from .utils import TEMPLATES, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("tf", short_help="tf (sampleapp.tf)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def tf(ctx: click.Context, **_: Any) -> None:  # pylint: disable=invalid-name
    """Generate a sample Terraform project."""
    src = TEMPLATES / "terraform"
    dest = Path.cwd() / "sampleapp.tf"

    copy_sample(ctx, src, dest)

    if not (src / ".terraform-version").is_file():
        (dest / ".terraform-version").write_text(get_latest_tf_version())

    LOGGER.success("Sample Terraform app created at %s", dest)
