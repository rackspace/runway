"""Test runway.cfngin.hooks.docker._login."""
# pylint: disable=no-self-use
from copy import deepcopy
from typing import TYPE_CHECKING

from mock import MagicMock

from runway.cfngin.hooks.docker import login
from runway.cfngin.hooks.docker._login import LoginArgs
from runway.cfngin.hooks.docker.data_models import ElasticContainerRegistry
from runway.cfngin.hooks.docker.hook_data import DockerHookData

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.docker import DockerClient

    from ....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.docker._login"


def test_login(cfngin_context, mock_docker_client, mocker):
    # type: ("MockCFNginContext", "DockerClient", "MockerFixture") -> None
    """Test login."""
    args = LoginArgs(password="p@ssword", registry="dkr.test.com", username="test-user")
    mocker.patch.object(LoginArgs, "parse_obj", return_value=args)
    mock_login = mocker.patch.object(mock_docker_client, "login")
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    mock_from_cfngin_context = mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    assert login(context=cfngin_context, **args.dict()) == docker_hook_data
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    mock_login.assert_called_once_with(**args.dict())
    mock_update_context.assert_called_once_with(cfngin_context)


class TestLoginArgs(object):
    """Test runway.cfngin.hooks.docker._login.LoginArgs."""

    def test_determine_registry(self):
        """Test determine_registry."""
        assert (
            LoginArgs.determine_registry(context=None, ecr=True, registry="something")
            == "something"
        )

    def test_determine_registry_ecr(self, mocker):
        # type: ("MockerFixture") -> None
        """Test determine_registry ecr."""
        registry = ElasticContainerRegistry(
            account_id="123456012", aws_region="us-east-1"
        )
        mocker.patch(
            MODULE + ".ElasticContainerRegistry",
            parse_obj=MagicMock(return_value=registry),
        )
        assert (
            LoginArgs.determine_registry(context=None, ecr=True, registry=None)
            == registry.fqn
        )

    def test_init_default(self):
        # type: () -> None
        """Test init defalt."""
        args = {"password": "p@ssword", "username": "test-user"}
        obj = LoginArgs.parse_obj(deepcopy(args))
        assert not obj.dockercfg_path
        assert not obj.email
        assert obj.password == args["password"]
        assert not obj.registry
        assert obj.username == args["username"]

    def test_init_ecr(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init ecr."""
        context = MagicMock()
        registry = ElasticContainerRegistry(
            account_id="123456012", aws_region="us-east-1"
        )
        mock_determine_registry = mocker.patch.object(
            LoginArgs, "determine_registry", return_value=registry.fqn,
        )
        args = {
            "ecr": {"account_id": "123456012", "aws_region": "us-east-1"},
            "password": "p@ssword",
        }
        obj = LoginArgs.parse_obj(deepcopy(args), context=context)
        mock_determine_registry.assert_called_once_with(
            context=context, ecr=args["ecr"], registry=None
        )
        assert not obj.dockercfg_path
        assert not obj.email
        assert obj.password == args["password"]
        assert obj.registry == registry.fqn
        assert obj.username == "AWS"

    def test_init_other_registry(self):  # type: () -> None
        """Test init with "other" registry."""
        args = {
            "dockercfg_path": "./.docker/config.json",
            "email": "user@test.com",
            "password": "p@ssword",
            "username": "test-user",
            "registry": "dkr.test.com",
        }
        obj = LoginArgs.parse_obj(deepcopy(args))
        assert obj.dockercfg_path == args["dockercfg_path"]
        assert obj.email == args["email"]
        assert obj.password == args["password"]
        assert obj.registry == args["registry"]
        assert obj.username == args["username"]
