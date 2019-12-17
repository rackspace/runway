"""Runway configuration 'path' settings."""
# pylint: disable=unused-import
from typing import Optional, Dict, List, Tuple  # noqa: F401

import os
import logging
import six

from .sources.git import Git

LOGGER = logging.getLogger('runway')


class Path(object):  # pylint: disable=too-many-instance-attributes
    """Runway configuration 'path' settings object."""

    def __init__(self, module, env_root, cache_dir=None, git_source_class=Git):
        # type: (str, str, Optional[str])-> Path
        """Initialize."""
        if not cache_dir:
            cache_dir = os.path.expanduser("~/.runway_cache")  # type: str

        self.git_source_class = git_source_class  # type: Git
        self.env_root = env_root  # type: str
        self.cache_dir = cache_dir  # type: str
        (self.source,
         self.uri,
         self.location,
         self.options) = self.parse(module)  # type: Tuple[str]
        self.module_root = self.__get_module_root_dir(module)  # type: str

    def __get_module_root_dir(self, module):
        # type: (str) -> str
        """Retrieve the root directory location of the module being parsed."""
        if isinstance(module, six.string_types):
            module = {'path': module}  # type: Dict[str, str]

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
            return self.git_source_class(self.configuration, self.cache_dir).fetch()
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
        # type: (Dict[str, str]) -> Tuple[str]
        """Retrieve the source and location of the path variable."""
        source = 'local'  # type: str
        uri = ''  # type: str
        location = ''  # type: str
        options = ''  # type: str

        split_source_location = module.get('path', '').split('::')  # type: List[str]

        # Local path
        if len(split_source_location) != 2:
            location = split_source_location[0]  # type: str
            options = {}  # type: Dict
            return source, uri, location, options

        source = split_source_location[0]  # type: str
        temp_location = split_source_location[1]  # type: str

        location, options = cls.__parse_location_and_options(temp_location)  # type: List[str]
        uri, location = cls.__parse_uri_and_location(location)  # type: List[str]

        return source, uri, location, options

    @classmethod
    def __parse_uri_and_location(cls, uri_loc_str):
        # type: (str) -> List[str]
        """Given a location string extract the uri and remaining location values."""
        split_uri_location = uri_loc_str.split('//')  # type: List[str, str]
        location_string = '/'  # type: str

        if len(split_uri_location) == 3:
            location_string = split_uri_location[2]  # type: str

        return [
            '//'.join([split_uri_location[0], split_uri_location[1]]),
            location_string
        ]

    @classmethod
    def __parse_location_and_options(cls, loc_opt_str):
        # type: (str) -> List[str]
        """Given a location string extract the location variable and the remote module options."""
        split_location_options = loc_opt_str.split('?')  # type: List(str)
        location = split_location_options[0]  # type: str
        options = {}  # type: Dict

        if len(split_location_options) == 2:
            options = cls.__parse_options_dict(
                split_location_options[1]
            )  # type: Dict[str, str]

        return [location, options]

    @staticmethod
    def __parse_options_dict(options_str):
        # type: (str) -> Dict[str, str]
        """Convert the options string into a dict."""
        opts = options_str.split('&')  # type: List[str]
        res = {}  # Type: Dict

        for opt in opts:
            key, value = opt.split('=')  # type: List[str, str]
            res[key] = value  # type: str

        return res
