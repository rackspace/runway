"""Replicate the functionality of `docker image` CLI commands.

https://github.com/docker/docker-py/blob/master/docker/models/images.py

"""
import itertools
import logging
import re
from typing import TYPE_CHECKING, Any

import six
from docker.errors import BuildError
from docker.models.images import ImageCollection as _ImageCollection
from docker.utils.json_stream import json_stream

from ....._logging import PrefixAdaptor

if TYPE_CHECKING:
    from docker.models.images import Image

ROOT_LOGGER = logging.getLogger(__name__.replace("._", "."))
LOGGER = PrefixAdaptor("docker", ROOT_LOGGER, prefix_template="({prefix}) {msg}")


class ImageCollection(_ImageCollection):  # pylint: disable=abstract-method
    """Extends ``docker.models.images.ImageCollection`` for use with Runway."""

    def build(self, **kwargs):  # type: (Any) -> "Image"
        """Build an image and return in. Customized for Runway.

        Similar to the ``docker image build`` command.
        Either ``path`` or ``fileobject`` must be set.

        If you have a tar file for the Docker build context (including a
        Dockerfile) already, pass a readable file-like object to ``fileobj``
        and also pass ``custom_context=True``. If the stream is compressed
        also, set ``encoding`` to the correct value (e.g ``gzip``).

        If you want to get the raw output of the build, use the
        :py:meth:`~docker.api.build.BuildApiMixin.build` method in the
        low-level API.

        Args:
            path (str): Path to the directory containing the Dockerfile
            fileobj: A file object to use as the Dockerfile. (Or a file-like
                object)
            tag (str): A tag to add to the final image
            quiet (bool): Whether to return the status
            nocache (bool): Don't use the cache when set to ``True``
            rm (bool): Remove intermediate containers. The ``docker build``
                command now defaults to ``--rm=true``, but we have kept the old
                default of `False` to preserve backward compatibility
            timeout (int): HTTP timeout
            custom_context (bool): Optional if using ``fileobj``
            encoding (str): The encoding for a stream. Set to ``gzip`` for
                compressing
            pull (bool): Downloads any updates to the FROM image in Dockerfiles
            forcerm (bool): Always remove intermediate containers, even after
                unsuccessful builds
            dockerfile (str): path within the build context to the Dockerfile
            buildargs (dict): A dictionary of build arguments
            container_limits (dict): A dictionary of limits applied to each
                container created by the build process. Valid keys:
                - memory (int): set memory limit for build
                - memswap (int): Total memory (memory + swap), -1 to disable
                    swap
                - cpushares (int): CPU shares (relative weight)
                - cpusetcpus (str): CPUs in which to allow execution, e.g.,
                    ``"0-3"``, ``"0,1"``
            shmsize (int): Size of `/dev/shm` in bytes. The size must be
                greater than 0. If omitted the system uses 64MB
            labels (dict): A dictionary of labels to set on the image
            cache_from (list): A list of images used for build cache
                resolution
            target (str): Name of the build-stage to build in a multi-stage
                Dockerfile
            network_mode (str): networking mode for the run commands during
                build
            squash (bool): Squash the resulting images layers into a
                single layer.
            extra_hosts (dict): Extra hosts to add to /etc/hosts in building
                containers, as a mapping of hostname to IP address.
            platform (str): Platform in the format ``os[/arch[/variant]]``.
            isolation (str): Isolation technology used during build.
                Default: `None`.
            use_config_proxy (bool): If ``True``, and if the docker client
                configuration file (``~/.docker/config.json`` by default)
                contains a proxy configuration, the corresponding environment
                variables will be set in the container being built.

        Raises:
            :py:class:`docker.errors.BuildError`
                If there is an error during the build.
            :py:class:`docker.errors.APIError`
                If the server returns any other error.
            ``TypeError``
                If neither ``path`` nor ``fileobj`` is specified.

        """
        resp = self.client.api.build(**kwargs)
        if isinstance(resp, six.string_types):
            return self.get(resp)
        last_event = None
        image_id = None
        result_stream, internal_stream = itertools.tee(json_stream(resp))
        # added real-time logging
        for chunk in internal_stream:
            if "error" in chunk:
                LOGGER.error(chunk["error"].strip())
                raise BuildError(chunk["error"], result_stream)
            if "stream" in chunk:
                stream_msg = chunk["stream"]
                if re.search(r"^Step \d*\/\d* : \w", stream_msg):
                    LOGGER.info(stream_msg.strip())
                else:
                    match = re.search(
                        r"(^Successfully built |sha256:)([0-9a-f]+)$", stream_msg
                    )
                    if match:
                        image_id = match.group(2)
                        LOGGER.info(stream_msg.strip())
                    else:
                        LOGGER.verbose(stream_msg.strip())
            else:
                LOGGER.debug(chunk)
            last_event = chunk
        if image_id:
            return self.get(image_id)
        raise BuildError(last_event or "Unknown", result_stream)
