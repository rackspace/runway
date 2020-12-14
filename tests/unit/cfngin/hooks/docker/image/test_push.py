"""Test runway.cfngin.hooks.docker.image._push."""
# pylint: disable=no-self-use,protected-access
from typing import TYPE_CHECKING

from mock import MagicMock, call

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import push
from runway.cfngin.hooks.docker.image._push import ImagePushArgs

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.docker import DockerClient

    from .....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.docker.image._push"


def test_push(cfngin_context, mock_docker_client, mocker):
    # type: ("MockCFNginContext", "DockerClient", "MockerFixture") -> None
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
    docker_hook_data.client.api.push.assert_has_calls(  # pylint: disable=no-member
        [call(args.repo, tag=args.tags[0]), call(args.repo, tag=args.tags[1])]
    )
    mock_update_context.assert_called_once_with(cfngin_context)


class TestImagePushArgs(object):
    """Test runway.cfngin.hooks.docker.image._push.ImagePushArgs."""

    def test_determine_repo(self):
        """Test determine_repo."""
        assert (
            ImagePushArgs.determine_repo(
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
            ImagePushArgs.determine_repo(
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
            ImagePushArgs.determine_repo(
                context=None, ecr_repo=True, image=mock_image, repo=None
            )
            == repo
        )

    def test_determine_repo_none(self):  # type: () -> None
        """Test determine_repo None."""
        assert not ImagePushArgs.determine_repo(
            context=None, ecr_repo={}, image=None, repo=None
        )

    def test_init_default(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init default values."""
        mock_determine_repo = mocker.patch.object(
            ImagePushArgs, "determine_repo", return_value="dkr.test.com/image"
        )
        obj = ImagePushArgs()
        mock_determine_repo.assert_called_once_with(
            context=None, ecr_repo=None, image=None, repo=None
        )
        assert obj.repo == mock_determine_repo.return_value
        assert obj.tags == ["latest"]

    def test_init_image(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init Image."""
        repo = "dkr.test.com/image"
        tags = ["latest", "oldest"]
        mock_image = MagicMock(spec=DockerImage, repo=repo, tags=tags)
        mock_determine_repo = mocker.patch.object(
            ImagePushArgs, "determine_repo", return_value=repo
        )
        obj = ImagePushArgs(image=mock_image)
        mock_determine_repo.assert_called_once_with(
            context=None, ecr_repo=None, image=mock_image, repo=None
        )
        assert obj.repo == repo
        assert obj.tags == tags

        # ensure tags are not overwritten if provided
        assert ImagePushArgs(image=mock_image, tags=["oldest"]).tags == ["oldest"]
