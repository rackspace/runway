"""``runway docs`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
import os
from typing import Any  # pylint: disable=W

import click

from ...util import SafeHaven
from .. import options

LOGGER = logging.getLogger(__name__.replace("._", "."))

DOCS_URL = "https://docs.onica.com/projects/runway/"


@click.command("docs", short_help="open doc site")
@options.debug
@options.no_color
@options.verbose
def docs(**_):
    # type: (Any) -> None
    """Open the Runway documentation web site using the default web browser."""
    with SafeHaven():
        # Pyinstaller sets this var on systems to force using the internal lib
        # but, this can break some functionally around opening a web browser
        # using click so, reset/remove the var.
        lp_key = "LD_LIBRARY_PATH"  # for GNU/Linux and *BSD.
        lp_orig = os.getenv(lp_key + "_ORIG")
        if lp_orig:
            LOGGER.debug("temporarily reverting environ: %s=%s", lp_key, lp_orig)
            os.environ[lp_key] = lp_orig  # restore the original, unmodified value
        else:
            # This happens when LD_LIBRARY_PATH was not set.
            # Remove the env var as a last resort:
            LOGGER.debug("temporarily removing environ: %s", lp_key)
            os.environ.pop(lp_key, None)
        LOGGER.verbose("launching url: %s", DOCS_URL)
        click.launch(DOCS_URL)
