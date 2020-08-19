"""``runway preflight`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging

import click

from .. import options
from ._test import test

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("preflight", short_help="alias of test")
@options.debug
@options.deploy_environment
@options.no_color
@options.verbose
@click.pass_context
def preflight(ctx, **kwargs):
    """Alias of "runway test"."""
    LOGGER.verbose("forwarding to test...")
    ctx.forward(test, **kwargs)
