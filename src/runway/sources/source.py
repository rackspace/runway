"""
Abstract parent class for a 'Source' type object.

Allows us to specify specific remote sourced resources for out application
(Git, S3, ect.)
"""
# pylint: disable=unused-import
from typing import Dict, Optional  # noqa: F401


class Source(object):
    """
    Abstract parent class for a 'Source' type object.

    Allows us to specify specific remote sourced resources for our application
    (Git, S3, ect.)
    """

    def __init__(self, config, cache_dir=None):
        # type(Dict[str, str or Dict[str, str]], Optional(str)) -> Source
        """Initialize."""
        self.config = config
        self.cache_dir = cache_dir

    def fetch(self):
        # type: () -> None
        """Retrieve remote source. To be implemented in each subclass."""
        raise NotImplementedError

    @staticmethod
    def sanitize_directory_path(uri):
        # type: (str) -> str
        """Sanitize a Source directory path string."""
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')
        return uri
