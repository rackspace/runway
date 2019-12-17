"""
Abstract parent class for a 'Source' type object.

Allows us to specify specific remote sourced resources for out application
(Git, S3, ect.)
"""
# pylint: disable=unused-import
from typing import Dict, Optional, Union  # noqa: F401

import os


class Source(object):
    """
    Abstract parent class for a 'Source' type object.

    Allows us to specify specific remote sourced resources for our application
    (Git, S3, ect.)
    """

    def __init__(self, config):
        # type(Dict[str, Union[str, Dict[str, str]]], Optional[str]) -> Source
        """Initialize."""

        self.cache_dir = config.get('cache_dir', None)

        if not self.cache_dir:
            self.cache_dir = os.path.expanduser("~/.runway_cache")  # type: str

        self.config = config  # type: Dict[str, Union[str, Dict[str, str]]]
        self.__create_cache_directory()

    def fetch(self):
        # type: () -> None
        """Retrieve remote source. To be implemented in each subclass."""
        raise NotImplementedError

    @staticmethod
    def sanitize_directory_path(uri):
        # type: (str) -> str
        """Sanitize a Source directory path string."""
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')  # type: str
        return uri

    def __create_cache_directory(self):
        # type: () -> None
        """If no cache directory exists for the remote runway modules, create one."""
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

