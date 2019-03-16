"""Collect all the command classes together."""

from .runway import init # noqa
from .runway import gen_sample  # noqa

from .modules import deploy # noqa
from .modules import destroy # noqa
from .modules import dismantle # noqa
from .modules import plan  # noqa
from .modules import preflight   # noqa
from .modules import takeoff   # noqa
from .modules import taxi  # noqa
from .modules import gitclean  # noqa
from .modules import test  # noqa
from .modules import whichenv  # noqa
