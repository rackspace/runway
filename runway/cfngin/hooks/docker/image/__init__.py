"""Docker image actions.

Replicates the functionality of ``docker image`` CLI commands.

"""
from ._build import build
from ._push import push
from ._remove import remove

__all__ = ["build", "push", "remove"]
