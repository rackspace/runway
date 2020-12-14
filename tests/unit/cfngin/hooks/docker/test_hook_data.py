"""Test runway.cfngin.hooks.docker.hook_data."""
# pylint: disable=no-self-use
from typing import TYPE_CHECKING

from runway.cfngin.hooks.docker.hook_data import DockerHookData

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.docker.hook_data"


class TestDockerHookData(object):
    """Test runway.cfngin.hooks.docker._hook_data.DockerHookData."""

    def test_client(self, mocker):
        # type: ("MockerFixture") -> None
        """Test client."""
        mock_local_client = mocker.patch(MODULE + ".DockerClient")
        obj = DockerHookData()
        assert obj.client == mock_local_client.from_env.return_value

    def test_from_cfngin_context(self, cfngin_context):
        # type: ("MockCFNginContext") -> None
        """Test from_cfngin_context."""
        obj = DockerHookData.from_cfngin_context(cfngin_context)
        assert isinstance(obj, DockerHookData)
        assert cfngin_context.hook_data["docker"] == obj
        # compare instance id as these should be the same instance
        assert id(DockerHookData.from_cfngin_context(cfngin_context)) == id(obj)

        cfngin_context.hook_data["docker"] = "something"
        new_obj = DockerHookData.from_cfngin_context(cfngin_context)
        # compare instance id as these should NOT be the same instance
        assert id(obj) != id(new_obj)

    def test_update_context(self, cfngin_context):
        # type: ("MockCFNginContext") -> None
        """Test update_context."""
        obj = DockerHookData()
        assert obj.update_context(cfngin_context) == obj
        assert cfngin_context.hook_data["docker"] == obj
        assert not obj.update_context()
