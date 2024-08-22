"""Test runway.cfngin.hooks.docker.image._remove."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call

from docker.errors import ImageNotFound
from docker.models.images import Image

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import remove
from runway.cfngin.hooks.docker.image._remove import ImageRemoveArgs

if TYPE_CHECKING:
    from docker import DockerClient
    from pytest_mock import MockerFixture

    from .....factories import MockCfnginContext

MODULE = "runway.cfngin.hooks.docker.image._remove"


def test_remove(
    cfngin_context: MockCfnginContext,
    mock_docker_client: DockerClient,
    mocker: MockerFixture,
) -> None:
    """Test remove."""
    repo = "dkr.test.com/image"
    tags = ["latest", "oldest"]
    image = DockerImage(image=Image({"RepoTags": [f"{repo}:{tag}" for tag in tags]}))
    args = ImageRemoveArgs(force=True, image=image, tags=["latest", "oldest"])
    mocker.patch.object(ImageRemoveArgs, "model_validate", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    docker_hook_data.image = image
    mock_from_cfngin_context = mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    assert (
        remove(context=cfngin_context, force=args.force, image=image, tags=args.tags)
        == docker_hook_data
    )
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    docker_hook_data.client.api.remove_image.assert_has_calls(  # type: ignore
        [call(force=True, image=f"{args.repo}:{tag}", noprune=False) for tag in args.tags]
    )
    assert docker_hook_data.image is None
    mock_update_context.assert_called_once_with(cfngin_context)


def test_remove_image_not_found(
    cfngin_context: MockCfnginContext,
    mock_docker_client: DockerClient,
    mocker: MockerFixture,
) -> None:
    """Test remove ImageNotFound."""
    args = ImageRemoveArgs(repo="dkr.test.com/image", tags=["latest"])
    mocker.patch.object(ImageRemoveArgs, "model_validate", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    mocker.patch.object(DockerHookData, "from_cfngin_context", return_value=docker_hook_data)
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    docker_hook_data.client.api.remove_image.side_effect = ImageNotFound(  # type: ignore
        f"{args.repo}:latest"
    )
    assert remove(context=cfngin_context, **args.model_dump()) == docker_hook_data
    docker_hook_data.client.api.remove_image.assert_has_calls(  # type: ignore
        [call(force=False, image=f"{args.repo}:{tag}", noprune=False) for tag in args.tags]
    )
    mock_update_context.assert_called_once_with(cfngin_context)


class TestImageRemoveArgs:
    """Test runway.cfngin.hooks.docker.image._remove.ImageRemoveArgs."""

    def test__set_ecr_repo_from_dict(self) -> None:
        """Test _set_ecr_repo from Dict."""
        args = {
            "repo_name": "foo",
            "account_id": "123",
            "registry_alias": "bar",
            "aws_region": "us-west-2",
        }
        obj = ImageRemoveArgs.model_validate({"ecr_repo": args})
        assert obj.ecr_repo
        assert obj.ecr_repo.name == args["repo_name"]
        assert obj.ecr_repo.registry.account_id == args["account_id"]
        assert obj.ecr_repo.registry.alias == args["registry_alias"]
        assert obj.ecr_repo.registry.region == args["aws_region"]

    def test__set_repo(self) -> None:
        """Test _set_repo."""
        assert ImageRemoveArgs(repo="something").repo == "something"
        assert not ImageRemoveArgs().repo

    def test__set_repo_ecr(self) -> None:
        """Test _set_repo ECR."""
        repo = ElasticContainerRegistryRepository(
            name="test",
            registry=ElasticContainerRegistry(account_id="123456789012", aws_region="us-east-1"),
        )
        assert ImageRemoveArgs(ecr_repo=repo).repo == repo.fqn

    def test__set_repo_image(self, mocker: MockerFixture) -> None:
        """Test _set_repo image."""
        mocker.patch.object(Image, "reload")
        image = DockerImage(image=Image({"RepoTags": ["foo:latest"]}))
        assert ImageRemoveArgs(image=image).repo == image.repo

    def test__set_tags(self) -> None:
        """Test _set_tags."""
        assert ImageRemoveArgs(tags=["foo"]).tags == ["foo"]
        assert ImageRemoveArgs().tags == ["latest"]

    def test__set_tags_image(self, mocker: MockerFixture) -> None:
        """Test _set_tags image."""
        mocker.patch.object(Image, "reload")
        image = DockerImage(image=Image({"RepoTags": ["foo:bar"]}))
        assert ImageRemoveArgs(image=image).tags == image.tags
