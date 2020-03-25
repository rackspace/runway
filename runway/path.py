"""Runway configuration 'path' settings."""
# pylint: disable=unused-import
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import os
import logging
import six

from .sources.git import Git

LOGGER = logging.getLogger('runway')


class Path(object):  # pylint: disable=too-many-instance-attributes
    """Runway configuration ``path`` settings object.

    Path is responsible for parsing the ``path`` property of a Runway
    configuration. It then can determine if the path specified is
    locally sourced or remotely sourced through a service such
    as `Git`_ or S3.

    Local ``path`` variables are defined relative to the root project folder.
    The value for this cannot be higher than the Runway config file, it must
    be at the runway file itself or in a sub directory.

    Example:
        .. code-block:: yaml

            deployments:
            - modules:
                - path: my/local/module.cfn
                - my/local/module.cfn # same as above
                - ./ # module is in the root

    When the ``path`` is remote, Runway is responsible for fetching
    the resource and returning the location of it's cached path.
    The information for retrieving those sources can be controlled via
    runway rather than manually retrieving each one.

    Example:
        .. code-block:: yaml

            deployments:
            - modules:
                - path: git::git://github.com/your_handle/your_repo.git//my-module.cfn


    The ``path`` structure is based on the
    encoding found in
    `Terraform modules <https://www.terraform.io/docs/modules/sources.html>`_.

    The values parsed from the string are as follows:

    .. rubric:: source

    Determine if the source is local or remote. The initial
    prefix is used to determine this separated by `::` in the string.
    A path is considered local if it contains no source type value.

    Example:
        .. code-block:: yaml

            deployments:
                - modules:
                    # source is `git`
                    - path: git::git://github.com/foo/bar.git

    .. rubric:: uri

    The uniform resource identifier when targetting a remote resource.
    This instructs runway on where to retrieve your module.

    Example:
        .. code-block:: yaml

            deployments:
                - modules:
                    # uri is `git://github.com/foo/bar.git`
                    - path: git::git://github.com/foo/bar.git

    .. rubric:: location

    The relative location of the module files from the root
    directory. This value is specified as a path after the uri separated
    by `//`

    Example:
        .. code-block:: yaml

            deployments:
                - modules:
                    # location is `my/path`
                    - path: git::git://github.com/foo/bar.git//my/path

    .. rubric:: options

    The remaining options that are passed along to the
    Source. This is specified in the path following the `?` separator.
    Multiple option keys and values can be specified with the `&` as
    the separator. Each remote source can have different options for
    retrieval, please make sure to review individual source types
    to get more information on properly formatting.

    Example:
        .. code-block:: yaml

            deployments:
                - modules:
                    # options are `foo=bar&ba=bop`
                    - path: git::git://github.com/foo/bar.git//my/path?foo=bar&baz=bop

    """

    def __init__(self, module, env_root, cache_dir=None, git_source_class=Git):
        # type: (Union(str, Dict[str, str]), str, Optional[str], Optional[Git])-> Path
        """Path Configuration.

        Keyword Args:
            module (Union(str, Dict[str, str])): The module manifest or a string
                representation of a local path to a module.
            env_root (str):  The current environments root directory path
                string.
            cache_dir (Optional[str]): When a remote resource is requested it's
                Source object requires a cache directory to store it's request.
                This allows for an override of that default directory.
            git_source_class (Optional[Git]): Dependency injection for the `Git`
                type Source.

        References:
            `Git`_

        """
        if isinstance(module, six.string_types):
            module = {'path': module}  # type: Dict[str, str]

        self.git_source_class = git_source_class  # type: Git
        self.env_root = env_root  # type: str
        self.cache_dir = cache_dir  # type: str
        (self.source,
         self.uri,
         self.location,
         self.options) = self.parse(module)  # type: Tuple[str]
        self.module_root = self.__get_module_root_dir()  # type: str

    def __get_module_root_dir(self):
        # type: () -> str
        """Get module root directory.

        Retrieve the specific path location of the module. This can be static
        or dynamically generated by a remote resource Source object.
        """
        if self.location in ['.', '.' + os.sep]:
            return self.env_root
        if self.source != 'local':
            return self.__fetch_remote_source()
        return os.path.join(self.env_root, self.location)

    def __fetch_remote_source(self):
        # type: () -> Union(Git, None)
        """
        Switch based on the retrieved source of the path.

        Determine which remote Source type to fetch based on the source
        specified in the path variable.
        """
        if self.source == 'git':
            return self.git_source_class(**self.configuration).fetch()
        return None

    @property
    def configuration(self):
        # type: () -> Dict[str, str]
        """Transform object into configuration settings for remote Sources."""
        return {
            'source': self.source,
            'location': self.location,
            'uri': self.uri,
            'options': self.options,
            'cache_dir': self.cache_dir
        }

    @classmethod
    def parse(cls, module):
        # type: (Dict[str, str]) -> Tuple[str]
        """Retrieve the relevant elements of the path variable passed.

        Keyword Args:
            module (Dict[str, str]): The module manifest or a string
                representation of a local path to a module.

        Given a dictionary with a `path` parameter parse the value into
        it's specific components. The path structure is based on the
        encoding found in
        `Terraform modules <https://www.terraform.io/docs/modules/sources.html>`_.
        """
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
        """Given a string extract the uri and remaining location values.

        Keyword Args:
            uri_loc_str (str): The string that represents the uri and
                remaining location values.

        Separator used is `//`. It is expected the uri will contain a
        protocol reference, so if a remote uri is used those values
        will be concatenated together.
        """
        split_uri_location = uri_loc_str.split('//')  # type: List[str, str]
        location_string = ''  # type: str

        if len(split_uri_location) == 3:
            location_string = split_uri_location[2]  # type: str

        return [
            '//'.join([split_uri_location[0], split_uri_location[1]]),
            location_string
        ]

    @classmethod
    def __parse_location_and_options(cls, loc_opt_str):
        # type: (str) -> List[str]
        """Given a location string extract the location variable and the remote module options.

        Keyword Args:
            loc_opt_str (str): The string that represents the location
                and remaining option values

        Seperator used is `?`. Each of the options retrieved are then
        turned into a Dict for easy accessibility based on the `&` separator
        """
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
        """Convert the options string into a dict.

        Keyword Args:
            options_str (str): The options string that will
                be seperated into a dictionary based on the
                `&` separator
        """
        opts = options_str.split('&')  # type: List[str]
        res = {}  # Type: Dict

        for opt in opts:
            key, value = opt.split('=')  # type: List[str, str]
            res[key] = value  # type: str

        return res
