"""``runway gen-sample cdk-csharp`` command."""
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


@click.command("cdk-csharp", short_help="cdk + c# (sampleapp.cdk)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def cdk_csharp(ctx, **_):
    # type: (click.Context, Any) -> None
    """Generate a sample AWS CDK project using C#."""
    src = TEMPLATES / "cdk-csharp"
    dest = Path.cwd() / "sampleapp.cdk"

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / "dot_gitignore")

    LOGGER.success("Sample C# CDK module created at %s", dest)
    LOGGER.notice(
        "To finish it's setup, change to the %s directory and execute"
        ' "npm install" to generate it\'s lockfile.',
        dest,
    )
