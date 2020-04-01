"""Collect all the command classes together."""

from .r4y import envvars # noqa
from .r4y import gen_sample  # noqa
from .r4y import init # noqa
from .r4y import preflight   # noqa
from .r4y import run_aws  # noqa
from .r4y import run_python  # noqa
from .r4y import run_stacker  # noqa
from .r4y import test  # noqa
from .r4y import tfenv  # noqa
from .r4y import kbenv  # noqa
from .r4y import whichenv  # noqa

from .modules import deploy # noqa
from .modules import destroy # noqa
from .modules import dismantle # noqa
from .modules import plan  # noqa
from .modules import takeoff   # noqa
from .modules import taxi  # noqa
