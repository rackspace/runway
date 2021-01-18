"""``runway gen-sample cfngin`` command."""
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import ROOT, TEMPLATES, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("cfngin", short_help="cfngin + troposphere (sampleapp.cfn)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def cfngin(ctx: click.Context, **_: Any) -> None:
    """Generate a sample CFNgin project using Blueprints."""
    src = TEMPLATES / "cfngin"
    src_blueprints = ROOT / "blueprints"
    dest = Path.cwd() / "sampleapp.cfn"
    blueprints = dest / "tfstate_blueprints"
    tf_state = blueprints / "tf_state.py"

    copy_sample(ctx, src, dest)

    blueprints.mkdir()
    LOGGER.debug('copying blueprint from "%s" to "%s"', src_blueprints, blueprints)
    shutil.copyfile(src_blueprints / "__init__.py", blueprints / "__init__.py")
    shutil.copyfile(src_blueprints / "tf_state.py", tf_state)
    tf_state.chmod(tf_state.stat().st_mode | 0o0111)
    LOGGER.success("Sample CFNgin module created at %s", dest)
