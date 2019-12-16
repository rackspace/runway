"""
Abstract parent class for a 'Source' type object.

Allows us to specify specific remote sourced resources for out application
(Git, S3, ect.)
"""


class Source(object):
    """
    Abstract parent class for a 'Source' type object.

    Allows us to specify specific remote sourced resources for our application
    (Git, S3, ect.)
    """

    def __init__(self, config, cache_dir=None):
        """Initialize."""
        self.config = config
        self.cache_dir = cache_dir

    def fetch(self):
        """Retrieve remote source. To be implemented in each subclass."""
        raise NotImplementedError

    def sanitize_directory_path(self, uri):
        """Sanitize a Source directory path string."""
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')
        return uri
