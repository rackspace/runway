"""Docker client."""
from docker.client import DockerClient as _DockerClient

from .models.images import ImageCollection


class DockerClient(_DockerClient):
    """A client for communicating with a Docker server.

    Subclassed from :py:class:`docker.client.DockerClient` to patch in features
    that enable improved integration with Runway.

    Example:
        >>> from runway.core.docker import DockerClient
        >>> client = DockerClient(base_url='unix://var/run/docker.sock')

    Args:
        base_url (str): URL to the Docker server. For example,
            ``unix:///var/run/docker.sock`` or ``tcp://127.0.0.1:1234``.
        version (str): The version of the API to use. Set to ``auto`` to
            automatically detect the server's version. Default: ``1.35``
        timeout (int): Default timeout for API calls, in seconds.
        tls (bool or :py:class:`~docker.tls.TLSConfig`): Enable TLS. Pass
            ``True`` to enable it with default options, or pass a
            :py:class:`~docker.tls.TLSConfig` object to use custom
            configuration.
        user_agent (str): Set a custom user agent for requests to the server.
        credstore_env (dict): Override environment variables when calling the
            credential store process.
        use_ssh_client (bool): If set to `True`, an ssh connection is made
            via shelling out to the ssh client. Ensure the ssh client is
            installed and configured on the host.
        max_pool_size (int): The maximum number of connections
            to save in the pool.

    """

    @property
    def images(self):  # type: () -> ImageCollection
        """Manage images on the server."""
        return ImageCollection(client=self)
