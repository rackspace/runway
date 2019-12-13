class Source(object):
    def sanitize_directory_path(self, uri):
        for i in ['@', '/', ':']:
            uri = uri.replace(i, '_')
        return uri
