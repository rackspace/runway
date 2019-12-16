"""
    Abstract parent class for a 'Source' type object.
    Allows us to specify specific remote sourced resources for out application
    (Git, S3, ect.)
"""
class Source(object):
    """
        Abstract parent class for a 'Source' type object.
        Allows us to specify specific remote sourced resources for out application
        (Git, S3, ect.)
    """

    def sanitize_directory_path(self, uri):
        """ Sanitize a Source directory path string """
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')
        return uri
