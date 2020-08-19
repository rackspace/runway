"""``runway whichenv`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging

import click

from ...util import SafeHaven
from .. import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("whichenv", short_help="current deploy environment")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def whichenv(ctx, **_):  # noqa: D301
    """Print the current deploy environment name to stdout.

    When run, the deploy environment will be determined from one of the
    following (in order of precedence):

    \b
      - "DEPLOY_ENVIRONMENT" environment variable
      - git branch name (strips "ENV-" prefix, master => common)
      - current working directory

    """
    if not (ctx.obj.debug or ctx.obj.verbose):
        logging.getLogger("runway").setLevel(logging.ERROR)  # suppress warnings
    with SafeHaven(environ={"CI": "1"}):  # prevent prompts
        click.echo(ctx.obj.env.name)
