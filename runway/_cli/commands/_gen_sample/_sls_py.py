"""``runway gen-sample sls-py`` command."""
import logging
import sys
from typing import Any  # pylint: disable=W

import click

from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("sls-py", short_help="sls + python (sampleapp.sls)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def sls_py(ctx, **_):
    # type: (click.Context, Any) -> None
    """Generate a sample Serverless project using python."""
    src = TEMPLATES / "sls-py"
    dest = Path.cwd() / "sampleapp.sls"

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / "_gitignore")

    LOGGER.success("Sample Serverless module created at %s", dest)
    LOGGER.notice(
        "To finish it's setup, change to the %s directory and "
        'execute "npm install" to generate it\'s lockfile.',
        dest,
    )
