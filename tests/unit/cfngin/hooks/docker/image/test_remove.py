"""Test runway.cfngin.hooks.docker.image._remove."""
# pylint: disable=no-self-use,protected-access
from typing import TYPE_CHECKING

import pytest
from docker.errors import ImageNotFound
from mock import MagicMock, call

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import remove
from runway.cfngin.hooks.docker.image._remove import ImageRemoveArgs

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.docker import DockerClient

    from .....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.docker.image._remove"


def test_remove(cfngin_context, mock_docker_client, mocker):
    # type: ("MockCFNginContext", "DockerClient", "MockerFixture") -> None
    """Test remove."""
    repo = "dkr.test.com/image"
    tags = ["latest", "oldest"]
    mock_image = MagicMock(
        spec=DockerImage, tags=["{}:{}".format(repo, tag) for tag in tags]
    )
    mock_image.attrs = {"RepoTags": mock_image.tags}
    args = ImageRemoveArgs(force=True, image=mock_image, tags=["latest", "oldest"])
    mocker.patch.object(ImageRemoveArgs, "parse_obj", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    docker_hook_data.image = mock_image
    mock_from_cfngin_context = mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    assert (
        remove(
            context=cfngin_context, force=args.force, image=mock_image, tags=args.tags
        )
        == docker_hook_data
    )
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    docker_hook_data.client.api.remove_image.assert_has_calls(  # pylint: disable=no-member
        [
            call(force=True, image="{}:{}".format(args.repo, tag), noprune=False)
            for tag in args.tags
        ]
    )
    assert docker_hook_data.image is None
    mock_update_context.assert_called_once_with(cfngin_context)


def test_remove_image_not_found(cfngin_context, mock_docker_client, mocker):
    # type: ("MockCFNginContext", "DockerClient", "MockerFixture") -> None
    """Test remove ImageNotFound."""
    args = ImageRemoveArgs(repo="dkr.test.com/image", tags=["latest"])
    mocker.patch.object(ImageRemoveArgs, "parse_obj", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_docker_client)
    docker_hook_data = DockerHookData()
    mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    docker_hook_data.client.api.remove_image.side_effect = ImageNotFound(
        args.repo + ":latest"
    )
    assert remove(context=cfngin_context, **args.dict()) == docker_hook_data
    docker_hook_data.client.api.remove_image.assert_has_calls(  # pylint: disable=no-member
        [
            call(force=False, image="{}:{}".format(args.repo, tag), noprune=False)
            for tag in args.tags
        ]
    )
    mock_update_context.assert_called_once_with(cfngin_context)


class TestImageRemoveArgs(object):
    """Test runway.cfngin.hooks.docker.image._remove.ImageRemoveArgs."""

    def test_determine_repo(self):
        """Test determine_repo."""
        assert (
            ImageRemoveArgs.determine_repo(
                context=None, ecr_repo={"key": "val"}, image=None, repo="something"
            )
            == "something"
        )

    def test_determine_repo_ecr(self, mocker):
        # type: ("MockerFixture") -> None
        """Test determine_repo ecr."""
        repo = ElasticContainerRegistryRepository(
            account_id="123456012", aws_region="us-east-1", repo_name="test"
        )
        mocker.patch(
            MODULE + ".ElasticContainerRegistryRepository",
            parse_obj=MagicMock(return_value=repo),
        )
        assert (
            ImageRemoveArgs.determine_repo(
                context=None,
                ecr_repo={
                    "repo_name": repo.name,
                    "account_id": repo.registry.account_id,
                    "aws_region": repo.registry.region,
                },
                image=None,
                repo=None,
            )
            == repo.fqn
        )

    def test_determine_repo_image(self):  # type: () -> None
        """Test determine_repo Image."""
        repo = "dkr.test.com/image"
        mock_image = MagicMock(spec=DockerImage, repo=repo)
        assert (
            ImageRemoveArgs.determine_repo(
                context=None, ecr_repo=True, image=mock_image, repo=None
            )
            == repo
        )

    def test_determine_repo_none(self):  # type: () -> None
        """Test determine_repo None."""
        with pytest.raises(ValueError):
            ImageRemoveArgs.determine_repo(
                context=None, ecr_repo={}, image=None, repo=None
            )

    def test_init_default(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init default values."""
        mock_determine_repo = mocker.patch.object(
            ImageRemoveArgs, "determine_repo", return_value="dkr.test.com/image"
        )
        obj = ImageRemoveArgs()
        mock_determine_repo.assert_called_once_with(
            context=None, ecr_repo=None, image=None, repo=None
        )
        assert obj.force is False
        assert obj.noprune is False
        assert obj.repo == mock_determine_repo.return_value
        assert obj.tags == ["latest"]

    def test_init_image(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init Image."""
        repo = "dkr.test.com/image"
        tags = ["latest", "oldest"]
        mock_image = MagicMock(spec=DockerImage, repo=repo, tags=tags)
        mock_determine_repo = mocker.patch.object(
            ImageRemoveArgs, "determine_repo", return_value=repo
        )
        obj = ImageRemoveArgs(force=True, image=mock_image, noprune=True)
        mock_determine_repo.assert_called_once_with(
            context=None, ecr_repo=None, image=mock_image, repo=None
        )
        assert obj.force is True
        assert obj.noprune is True
        assert obj.repo == repo
        assert obj.tags == tags

        # ensure tags are not overwritten if provided
        assert ImageRemoveArgs(image=mock_image, tags=["oldest"]).tags == ["oldest"]
