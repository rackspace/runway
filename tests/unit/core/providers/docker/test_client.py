"""Test runway.core.providers.docker.client."""
# pylint: disable=no-self-use,too-few-public-methods
from typing import TYPE_CHECKING

from runway.core.providers.docker import DockerClient

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.docker.client"


class TestDockerClient(object):
    """Test runway.core.providers.docker.client.DockerClient."""

    def test_images(self, mocker):  # type: ("MockerFixture") -> None
        """Test images."""
        mock_image_collection = mocker.patch(MODULE + ".ImageCollection")
        client = DockerClient()
        assert client.images == mock_image_collection.return_value
        mock_image_collection.assert_called_once_with(client=client)
