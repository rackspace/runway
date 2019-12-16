""" Runway configuration 'path' settings """
import os
import logging
import six

from .sources.git import Git

LOGGER = logging.getLogger('runway')

class Path(object):
    """ Runway configuration 'path' settings object """

    def __init__(self, module, env_root, cache_dir=None):
        """ Initialize. """
        if not cache_dir:
            cache_dir = os.path.expanduser("~/.runway_cache")

        self.module = module
        self.env_root = env_root
        self.cache_dir = cache_dir
        self.source, self.location = self.get_source_and_location()
        self.config = self.get_config()
        self.module_root = self.get_module_root()

    def get_source_and_location(self):
        """ Retrieve the source and location of the path variable """

        res = ['local', '']
        sp = self.module['path'].split('::')

        if len(sp) == 2:
            res[0] = sp[0]
            res[1] = sp[1]
        else:
            res[1] = sp[0]
        return res

    def get_module_root(self):
        if isinstance(self.module, six.string_types):
            self.module = {'path': self.module}

        if self.location in ['.', '.' + os.sep]:
            return self.env_root
        if self.source != 'local':
            self.create_cache_directory()
            return self.fetch_remote_source()
        return os.path.join(self.env_root, self.location)

    def get_config(self):
        conf = {}
        params = self.location.split('>')
        conf = { key: value for key, value in [param.split('=') for param in params[1:]] }
        conf['uri'] = params[0]

        return conf

    def create_cache_directory(self):
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

    def fetch_remote_source(self):
        if self.source == 'git':
            return Git(self.config, self.cache_dir).fetch()
