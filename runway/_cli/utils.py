"""CLI utils."""
import logging
import sys
from typing import Any, Iterator  # noqa pylint: disable=W

from six.moves.collections_abc import MutableMapping  # pylint: disable=E

from ..core.components import DeployEnvironment
from ..commands.runway_command import get_env  # TODO update path
from ..config import Config
from ..util import cached_property

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


class CliContext(MutableMapping):
    """CLI context object."""

    def __init__(self, deploy_environment=None, **_):
        """Instantiate class."""
        self._deploy_environment = deploy_environment
        self.root_dir = Path.cwd()

    @cached_property
    def env(self):
        """Name of the current deploy environment."""
        return DeployEnvironment(
            explicit_name=self._deploy_environment,
            ignore_git_branch=self.runway_config.ignore_git_branch,
            root_dir=self.root_dir
        )

    @cached_property
    def runway_config(self):
        # type: () -> Config
        """Runway config."""
        return Config.load_from_file(self.runway_config_path)

    @cached_property
    def runway_config_path(self):
        # type: () -> Path
        """Path to the runway config file."""
        try:
            return Config.find_config_file(config_dir=self.root_dir)
        except SystemExit:
            LOGGER.debug('')
            self.root_dir = self.root_dir.parent
            return Config.find_config_file(config_dir=self.root_dir)

    def get(self, key, default=None):
        # type: (str, Any) -> Any
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, key, default)

    def get_env(self, prompt_if_unexpected=False):
        """Get the current deploy environment."""
        return get_env(path=self.root_dir,
                       ignore_git_branch=self.runway_config.ignore_git_branch,
                       prompt_if_unexpected=prompt_if_unexpected)

    def __bool__(self):
        # type: () -> bool
        """Implement evaluation of instances as a bool."""
        return bool(self.__dict__)

    __nonzero__ = __bool__  # python2 compatability

    def __getitem__(self, key):
        # type: (str) -> Any
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            Attribute: If attribute does not exist on this object.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(obj['key'])
                # value

        """
        return getattr(self, key)

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        """Implement assignment to self[key].

        Args:
            key: Attribute name to associate with a value.
            value: Value of a key/attribute.

        Example:
            .. codeblock: python

                obj = MutableMap()
                obj['key'] = 'value'
                print(obj['key'])
                # value

        """
        setattr(self, key, value)

    def __delitem__(self, key):
        # type: (str) -> None
        """Implement deletion of self[key].

        Args:
            key: Attribute name to remove from the object.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                del obj['key']
                print(obj.__dict__)
                # {}

        """
        delattr(self, key)

    def __len__(self):
        # type: () -> int
        """Implement the built-in function len().

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(len(obj))
                # 1

        """
        return len(self.__dict__)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """Return iterator object that can iterate over all attributes.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                for k, v in obj.items():
                    print(f'{key}: {value}')
                # key: value

        """
        return iter(self.__dict__)

    def __str__(self):
        # type: () -> str
        """Return string representation of the object."""
        return 'CliContext({})'.format(self.__dict__)
