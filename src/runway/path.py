"""Runway configuration 'path' settings."""
# pylint: disable=unused-import
from typing import Optional, Dict, List, Tuple  # noqa: F401

import os
import logging
import six

from .sources.git import Git

LOGGER = logging.getLogger('runway')


class Path(object):
    """Runway configuration 'path' settings object."""

    def __init__(self, module, env_root, cache_dir=None):
        # type: (str, str, Optional[str])-> Path
        """Initialize."""
        if not cache_dir:
            cache_dir = os.path.expanduser("~/.runway_cache")

        self.env_root = env_root
        self.cache_dir = cache_dir
        self.source, self.uri, self.location, self.options = self.parse(module)
        self.module_root = self.__get_module_root_dir(module)

    def __get_module_root_dir(self, module):
        # type: (str) -> str
        """Retrieve the root directory location of the module being parsed."""
        if isinstance(module, six.string_types):
            module = {'path': module}

        if self.location in ['.', '.' + os.sep]:
            return self.env_root
        if self.source != 'local':
            self.__create_cache_directory()
            return self.__fetch_remote_source()
        return os.path.join(self.env_root, self.location)

    def __create_cache_directory(self):
        # type: () -> None
        """If no cache directory exists for the remote runway modules, create one."""
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

    def __fetch_remote_source(self):
        # type: () -> Git or None
        """
        Switch based on the retrieved source of the path.

        Determine which remote Source type to fetch.
        """
        if self.source == 'git':
            return Git(self.configuration, self.cache_dir).fetch()
        return None

    @property
    def configuration(self):
        # type: () -> Dict[str, str]
        """Transform object into configuration settings for remote sources."""
        return {
            'source': self.source,
            'location': self.location,
            'uri': self.uri,
            'options': self.options
        }

    @classmethod
    def parse(cls, module):
        # type: (str) -> Tuple[str]
        """Retrieve the source and location of the path variable."""
        source = 'local'
        uri = ''
        location = ''
        options = ''

        split_source_location = module.get('path', '').split('::')

        # Local path
        if len(split_source_location) != 2:
            location = split_source_location[0]
            return [source, uri, location, options]

        source = split_source_location[0]
        temp_location = split_source_location[1]

        uri, location = cls.__parse_uri_and_location(temp_location)
        location, options = cls.__parse_location_and_options(location)

        return source, uri, location, options

    @classmethod
    def __parse_uri_and_location(cls, uri_loc_str):
        # type: (str) -> List[str]
        """Given a location string extract the uri and remaining location values."""
        split_uri_location = uri_loc_str.split('//')
        location_string = '/'

        if len(split_uri_location) == 3:
            location_string = split_uri_location[2]

        return [
            '//'.join([split_uri_location[0], split_uri_location[1]]),
            location_string
        ]

    @classmethod
    def __parse_location_and_options(cls, loc_opt_str):
        # type: (str) -> List[str]
        """Given a location string extract the location variable and the remote module options."""
        split_location_options = loc_opt_str.split('?')
        location = split_location_options[0]
        options = {}

        if len(split_location_options) == 2:
            options = cls.__parse_options_dict(split_location_options[1])

        return [location, options]

    @staticmethod
    def __parse_options_dict(options_str):
        # type: (str) -> Dict[str, str]
        """Convert the options string into a dict."""
        opts = options_str.split('&')
        res = {}

        for opt in opts:
            key, value = opt.split('=')
            res[key] = value

        return res
