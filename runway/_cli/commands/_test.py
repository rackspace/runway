"""``runway test`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging

import click

from ...core import Runway
from .. import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("test", short_help="run tests")
@options.debug
@options.deploy_environment
@options.no_color
@options.verbose
@click.pass_context
def test(ctx, **_):
    """Execute tests as defined in the Runway config.

    If one of the tests fail, the command will exit immediately unless
    "required: false" is set on the failing test.

    If the failing test is not required, the next test will be executed.

    If any of the tests fail, the command will exit with a non-zero exit code.

    """
    Runway(ctx.obj.runway_config, ctx.obj.get_runway_context()).test()
