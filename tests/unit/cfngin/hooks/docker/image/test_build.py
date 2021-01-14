"""Test runway.cfngin.hooks.docker.image._build."""
# pylint: disable=no-self-use,protected-access
import sys
from copy import deepcopy
from typing import TYPE_CHECKING

import pytest
from docker.models.images import Image
from mock import MagicMock

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import build
from runway.cfngin.hooks.docker.image._build import (
    DockerImageBuildApiOptions,
    ImageBuildArgs,
)

from .....mock_docker.fake_api import FAKE_IMAGE_ID

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # type: ignore pylint: disable=E

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from .....factories import MockCFNginContext


MODULE = "runway.cfngin.hooks.docker.image._build"


def test_build(cfngin_context, mocker, tmp_path):
    # type: ("MockCFNginContext", "MockerFixture", Path) -> None
    """Test build."""
    (tmp_path / "Dockerfile").touch()
    mock_image = MagicMock(
        spec=Image, id=FAKE_IMAGE_ID, tags=MagicMock(return_value=["latest"])
    )
    mock_logs = [{"stream": "log message\n"}, {"not-stream": "no log"}]
    mock_client = MagicMock(
        images=MagicMock(build=MagicMock(return_value=(mock_image, mock_logs)))
    )
    args = ImageBuildArgs(path=tmp_path)
    mocker.patch.object(ImageBuildArgs, "parse_obj", return_value=args)
    mocker.patch.object(DockerHookData, "client", mock_client)
    docker_hook_data = DockerHookData()
    mock_from_cfngin_context = mocker.patch.object(
        DockerHookData, "from_cfngin_context", return_value=docker_hook_data
    )
    mock_update_context = mocker.patch.object(
        DockerHookData, "update_context", return_value=docker_hook_data
    )
    cfngin_context.hook_data["docker"] = docker_hook_data
    assert build(context=cfngin_context, **args.dict()) == docker_hook_data
    mock_from_cfngin_context.assert_called_once_with(cfngin_context)
    mock_client.images.build.assert_called_once_with(
        path=str(args.path), **args.docker.dict()
    )
    mock_image.tag.assert_called_once_with(None, tag="latest")
    mock_image.reload.assert_called_once()
    assert isinstance(docker_hook_data.image, DockerImage)
    assert docker_hook_data.image.image == mock_image
    mock_update_context.assert_called_once_with(cfngin_context)


class TestDockerImageBuildApiOptions(object):
    """Test runway.cfngin.hooks.docker.image._build.DockerImageBuildApiOptions."""

    def test_init(self):  # type: () -> None
        """Test init."""
        args = {
            "buildargs": {"key": "val"},
            "custom_context": True,
            "extra_hosts": {"host": "local"},
            "forcerm": True,
            "isolation": "yes",
            "network_mode": "host",
            "nocache": True,
            "platform": "x86",
            "pull": True,
            "rm": False,
            "squash": True,
            "tag": "latest",
            "target": "dev",
            "timeout": 3,
            "use_config_proxy": True,
        }
        obj = DockerImageBuildApiOptions(**deepcopy(args))
        assert obj.dict() == args

    def test_init_default(self):  # type: () -> None
        """Test init default."""
        obj = DockerImageBuildApiOptions()
        assert obj.buildargs == {}
        assert obj.custom_context is False
        assert not obj.extra_hosts
        assert obj.forcerm is False
        assert not obj.isolation
        assert not obj.network_mode
        assert obj.nocache is False
        assert not obj.platform
        assert obj.pull is False
        assert obj.rm is True
        assert obj.squash is False
        assert not obj.tag
        assert not obj.target
        assert not obj.timeout
        assert obj.use_config_proxy is False


class TestImageBuildArgs(object):
    """Test runway.cfngin.hooks.docker.image._build.ImageBuildArgs."""

    def test_determine_repo(self):
        """Test determine_repo."""
        assert (
            ImageBuildArgs.determine_repo(
                context=None, ecr_repo={"key": "val"}, repo="something"
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
            ImageBuildArgs.determine_repo(
                context=None,
                ecr_repo={
                    "repo_name": repo.name,
                    "account_id": repo.registry.account_id,
                    "aws_region": repo.registry.region,
                },
                repo=None,
            )
            == repo.fqn
        )

    def test_init(self, mocker, tmp_path):
        # type: ("MockerFixture", Path) -> None
        """Test init."""
        args = {
            "docker": {"pull": True},
            "dockerfile": "./dir/Dockerfile",
            "ecr_repo": {"name": "test"},
            "path": tmp_path,
            "repo": "ecr",
            "tags": ["oldest"],
        }
        context = MagicMock()
        mock_validate_dockerfile = mocker.patch.object(
            ImageBuildArgs, "_validate_dockerfile", return_value=args["dockerfile"]
        )
        mock_determine_repo = mocker.patch.object(
            ImageBuildArgs, "determine_repo", return_value="repo"
        )
        obj = ImageBuildArgs.parse_obj(args, context=context)
        assert obj.path == args["path"]
        mock_validate_dockerfile.assert_called_once_with(tmp_path, args["dockerfile"])
        assert obj.dockerfile == args["dockerfile"]
        mock_determine_repo.assert_called_once_with(
            context=context, ecr_repo=args["ecr_repo"], repo=args["repo"]
        )
        assert obj.repo == mock_determine_repo.return_value
        assert obj.tags == args["tags"]
        assert isinstance(obj.docker, DockerImageBuildApiOptions)
        assert obj.docker.tag == mock_determine_repo.return_value

    def test_init_default(self, mocker):
        # type: ("MockerFixture") -> None
        """Test init default values."""
        context = MagicMock()
        mock_validate_dockerfile = mocker.patch.object(
            ImageBuildArgs, "_validate_dockerfile", return_value="./Dockerfile"
        )
        obj = ImageBuildArgs(context=context)
        assert obj.path == Path.cwd()
        mock_validate_dockerfile.assert_called_once_with(Path.cwd(), "./Dockerfile")
        assert obj.dockerfile == mock_validate_dockerfile.return_value
        assert not obj.repo
        assert obj.tags == ["latest"]
        assert isinstance(obj.docker, DockerImageBuildApiOptions)

    def test_validate_dockerfile(self, tmp_path):
        # type: (Path) -> None
        """Test _validate_dockerfile."""
        (tmp_path / "Dockerfile").touch()
        assert (
            ImageBuildArgs._validate_dockerfile(tmp_path, "./Dockerfile")
            == "./Dockerfile"
        )

    def test_validate_dockerfile_does_not_exist(self, tmp_path):
        # type: (Path) -> None
        """Test _validate_dockerfile does not exist."""
        with pytest.raises(ValueError) as excinfo:
            ImageBuildArgs._validate_dockerfile(tmp_path, "./Dockerfile")
        assert str(excinfo.value).startswith("Dockerfile does not exist at path")

    def test_validate_dockerfile_path_is_dockerfile(self, tmp_path):
        # type: (Path) -> None
        """Test _validate_dockerfile does not exist."""
        path = tmp_path / "Dockerfile"
        path.touch()
        with pytest.raises(ValueError) as excinfo:
            ImageBuildArgs._validate_dockerfile(path, "./Dockerfile")
        assert str(excinfo.value).startswith(
            "ImageBuildArgs.path should not reference the Dockerfile directly"
        )

    def test_validate_dockerfile_path_is_zipfile(self, tmp_path):
        # type: (Path) -> None
        """Test _validate_dockerfile path is zipfile."""
        path = tmp_path / "something.zip"
        path.touch()
        assert (
            ImageBuildArgs._validate_dockerfile(path, "./Dockerfile") == "./Dockerfile"
        )
