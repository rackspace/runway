"""``runway gen-sample cdk-csharp`` command."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("cdk-csharp", short_help="cdk + c# (sampleapp.cdk)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def cdk_csharp(ctx: click.Context, **_: Any) -> None:
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
