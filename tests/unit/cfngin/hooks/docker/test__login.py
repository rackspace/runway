"""Test runway.cfngin.hooks.docker._login."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import pytest

from runway.cfngin.hooks.docker import login
from runway.cfngin.hooks.docker._login import LoginArgs
from runway.cfngin.hooks.docker.data_models import ElasticContainerRegistry
from runway.cfngin.hooks.docker.hook_data import DockerHookData

if TYPE_CHECKING:
    from docker import DockerClient
    from pytest_mock import MockerFixture

    from ....factories import MockCfnginContext

MODULE = "runway.cfngin.hooks.docker._login"


def test_login(
    cfngin_context: MockCfnginContext,
    mock_docker_client: DockerClient,
    mocker: MockerFixture,
) -> None:
    """Test login."""
    args = LoginArgs(password="p@ssword", registry="dkr.test.com", username="test-user")
    mocker.patch.object(LoginArgs, "model_validate", return_value=args)
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
    assert login(context=cfngin_context, **args.model_dump()) == docker_hook_data
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    mock_login.assert_called_once_with(**args.model_dump())
    mock_update_context.assert_called_once_with(cfngin_context)


class TestLoginArgs:
    """Test runway.cfngin.hooks.docker._login.LoginArgs."""

    def test__set_ecr(self, mocker: MockerFixture) -> None:
        """Test _set_ecr."""
        expected = ElasticContainerRegistry(alias="foobar")
        mock_model_validate = mocker.patch.object(
            ElasticContainerRegistry, "model_validate", return_value=expected
        )
        assert (
            LoginArgs.model_validate(
                {"ecr": expected.model_dump(), "password": "", "username": ""}
            ).ecr
            == expected
        )
        mock_model_validate.assert_called_once_with({"context": None, **expected.model_dump()})

    @pytest.mark.parametrize(
        "ecr, registry, expected",
        [
            (None, "something", "something"),
            (None, None, None),
            (ElasticContainerRegistry(alias="foobar"), "something", "something"),
            (
                ElasticContainerRegistry(alias="foobar"),
                None,
                ElasticContainerRegistry.PUBLIC_URI_TEMPLATE.format(registry_alias="foobar"),
            ),
        ],
    )
    def test__set_registry(
        self,
        ecr: ElasticContainerRegistry | None,
        expected: str | None,
        registry: str | None,
    ) -> None:
        """Test _set_registry."""
        assert LoginArgs(ecr=ecr, password="", registry=registry, username="").registry == expected

    def test_field_defaults(self) -> None:
        """Test field defaults."""
        args = {"password": "p@ssword", "username": "test-user"}
        obj = LoginArgs.model_validate(deepcopy(args))
        assert not obj.dockercfg_path
        assert not obj.ecr
        assert not obj.email
        assert obj.password == args["password"]
        assert not obj.registry
        assert obj.username == args["username"]
