"""Environment variable lookup."""
from typing import Any, TYPE_CHECKING  # noqa

from stacker.util import read_value_from_path

from .base import LookupHandler

if TYPE_CHECKING:
    from ...context import Context  # noqa

TYPE_NAME = "env"


class EnvLookup(LookupHandler):
    """Environment variable lookup."""

    @classmethod
    def handle(cls, value, context, **_):
        # type: (str, 'Context', Any) -> Any
        """Retrieve an environment variable.

        The value is retrieved from a copy of the current environment variables
        that is saved to the context object. These environment variables
        are manipulated at runtime by Runway to fill in additional values
        such as ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the
        current execution.

        Args:
            value: The value passed to the lookup.
            context: The current context object.

        """
        value = read_value_from_path(value)

        try:
            return context.env_vars[value]
        except KeyError:
            raise ValueError(
                '"{}" does not exist in the environment.'.format(value)
            )
