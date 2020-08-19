"""``runway gen-sample tf`` command."""
import logging
import sys
from typing import Any  # pylint: disable=W

import click

from ....env_mgr.tfenv import get_latest_tf_version
from ... import options
from .utils import TEMPLATES, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("tf", short_help="tf (sampleapp.tf)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def tf(ctx, **_):  # pylint: disable=invalid-name
    # type: (click.Context, Any) -> None
    """Generate a sample Terraform project."""
    src = TEMPLATES / "terraform"
    dest = Path.cwd() / "sampleapp.tf"

    copy_sample(ctx, src, dest)

    if not (src / ".terraform-version").is_file():
        (dest / ".terraform-version").write_text(get_latest_tf_version())

    LOGGER.success("Sample Terraform app created at %s", dest)
