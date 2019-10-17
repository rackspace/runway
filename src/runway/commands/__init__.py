"""Collect all the command classes together."""

from .runway import envvars # noqa
from .runway import gen_sample  # noqa
from .runway import init # noqa
from .runway import preflight   # noqa
from .runway import run_aws  # noqa
from .runway import run_python  # noqa
from .runway import run_stacker  # noqa
from .runway import test  # noqa
from .runway import tfenv  # noqa
from .runway import kbenv  # noqa
from .runway import whichenv  # noqa

from .modules import deploy # noqa
from .modules import destroy # noqa
from .modules import dismantle # noqa
from .modules import plan  # noqa
from .modules import takeoff   # noqa
from .modules import taxi  # noqa
