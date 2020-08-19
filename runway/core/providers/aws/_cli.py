"""AWS cli."""
import logging
from typing import List  # pylint: disable=W

from awscli.clidriver import create_clidriver

from ....util import SafeHaven

LOGGER = logging.getLogger(__name__.replace("._", "."))


def cli(cmd):
    # type: (List[str]) -> None
    """Invoke AWS command.

    Args:
        cmd: Command to be passed to awscli.

    Raises:
        RuntimeError: awscli returned a non-zero exit code.

    """
    LOGGER.debug("passing command to awscli: %s", " ".join(cmd))
    with SafeHaven(argv=cmd, environ={"LC_CTYPE": "en_US.UTF"}):
        exit_code = create_clidriver().main(cmd)
        if exit_code:  # non-zero exit code
            raise RuntimeError("AWS CLI exited with code {}".format(exit_code))
