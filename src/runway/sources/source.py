"""
Abstract parent class for a 'Source' type object.

Allows us to specify specific remote sourced resources for out application
(Git, S3, ect.)
"""
# pylint: disable=unused-import
from typing import Dict, Optional, Union  # noqa: F401

import os


class Source(object):
    """Abstract parent class for a 'Source' type object.

    The Source parent class allows us to specify remote resources
    for our application via services such as Git or S3.  A cache
    directory, as part of object's configuration, is automatically
    created by default in the users home directory: ``~/.runway_cache``.
    This folder can be overridden by specifying the ``cache_dir`` property
    in the configuration passed.

    Every Source type object is expected to have a ``fetch`` method which
    will return the folder path at where the module requested resides.
    """

    def __init__(self, config):
        # type(Dict[str, Union[str, Dict[str, str]]]) -> Source
        """
            Keyword Arguments:
                config (Dict[str, Union[str, Dict[str, str]]]): The configuration
                    dictionary for the Source. Each Source object may expect
                    it's own specific type of parameters. Attributes:
                        cache_dir (Optional[str]): The cache directory path that should
                        be used as the root folder to store downloaded remote items.

        """
        self.cache_dir = config.get('cache_dir', None)

        if not self.cache_dir:
            self.cache_dir = os.path.expanduser("~/.runway_cache")  # type: str

        self.config = config  # type: Dict[str, Union[str, Dict[str, str]]]
        self.__create_cache_directory()

    def fetch(self):
        # type: () -> None
        """Retrieve remote source. To be implemented in each subclass."""
        raise NotImplementedError

    def __create_cache_directory(self):
        # type: () -> None
        """If no cache directory exists for the remote runway modules, create one."""
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

    @staticmethod
    def sanitize_directory_path(uri):
        # type: (str) -> str
        """Sanitize a Source directory path string.

        Keyword Arguments:
            uri (str): The uniform resource identifier when targetting a remote resource.

        """
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')  # type: str
        return uri
