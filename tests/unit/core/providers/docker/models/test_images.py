"""Test runway.core.providers.docker.models.images."""
# pylint: disable=no-self-use,too-few-public-methods
from typing import TYPE_CHECKING

from docker.models.images import Image

from .....mock_docker.fake_api import FAKE_IMAGE_ID

if TYPE_CHECKING:
    from runway.core.providers.docker import DockerClient

MODULE = "runway.core.providers.docker.models.images"


class TestImageCollection(object):
    """Test runway.core.providers.docker.models.images.ImageCollection."""

    def test_build(self, mock_docker_client):  # type: ("DockerClient") -> None
        """Test build."""
        image = mock_docker_client.images.build()
        mock_docker_client.api.build.assert_called_with()
        mock_docker_client.api.inspect_image.assert_called_with(FAKE_IMAGE_ID)
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID
