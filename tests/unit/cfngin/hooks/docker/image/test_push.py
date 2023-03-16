"""Test runway.cfngin.hooks.docker.image._push."""
# pylint: disable=no-member
# pyright: basic, reportFunctionMemberAccess=none
from __future__ import annotations

from typing import TYPE_CHECKING

from docker.models.images import Image
from mock import call

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import push
from runway.cfngin.hooks.docker.image._push import ImagePushArgs

if TYPE_CHECKING:
    from docker import DockerClient
    from pytest_mock import MockerFixture

    from .....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.docker.image._push"


def test_push(
    cfngin_context: MockCFNginContext,
    mock_docker_client: DockerClient,
    mocker: MockerFixture,
) -> None:
    """Test push."""
    args = ImagePushArgs(repo="dkr.test.com/image", tags=["latest", "oldest"])
    mocker.patch.object(ImagePushArgs, "parse_obj", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    mock_from_cfngin_context = mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    assert push(context=cfngin_context, **args.dict()) == docker_hook_data
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    docker_hook_data.client.api.push.assert_has_calls(
        [call(args.repo, tag=args.tags[0]), call(args.repo, tag=args.tags[1])]
    )
    mock_update_context.assert_called_once_with(cfngin_context)


class TestImagePushArgs:
    """Test runway.cfngin.hooks.docker.image._push.ImagePushArgs."""

    def test__set_ecr_repo_from_dict(self) -> None:
        """Test _set_ecr_repo from Dict."""
        args = {
            "repo_name": "foo",
            "account_id": "123",
            "registry_alias": "bar",
            "aws_region": "us-west-2",
        }
        obj = ImagePushArgs.parse_obj({"ecr_repo": args})
        assert obj.ecr_repo
        assert obj.ecr_repo.name == args["repo_name"]
        assert obj.ecr_repo.registry.account_id == args["account_id"]
        assert obj.ecr_repo.registry.alias == args["registry_alias"]
        assert obj.ecr_repo.registry.region == args["aws_region"]

    def test__set_repo(self) -> None:
        """Test _set_repo."""
        assert ImagePushArgs(repo="something").repo == "something"
        assert not ImagePushArgs().repo

    def test__set_repo_ecr(self) -> None:
        """Test _set_repo ECR."""
        repo = ElasticContainerRegistryRepository(
            repo_name="test",
            registry=ElasticContainerRegistry(
                account_id="123456789012", aws_region="us-east-1"
            ),
        )
        assert ImagePushArgs(ecr_repo=repo).repo == repo.fqn

    def test__set_repo_image(self, mocker: MockerFixture) -> None:
        """Test _set_repo image."""
        mocker.patch.object(Image, "reload")
        image = DockerImage(image=Image({"RepoTags": ["foo:latest"]}))
        assert ImagePushArgs(image=image).repo == image.repo

    def test__set_tags(self) -> None:
        """Test _set_tags."""
        assert ImagePushArgs(tags=["foo"]).tags == ["foo"]
        assert ImagePushArgs().tags == ["latest"]

    def test__set_tags_image(self, mocker: MockerFixture) -> None:
        """Test _set_tags image."""
        mocker.patch.object(Image, "reload")
        image = DockerImage(image=Image({"RepoTags": ["foo:bar"]}))
        assert ImagePushArgs(image=image).tags == image.tags
