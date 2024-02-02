"""Test runway.cfngin.hooks.docker.image._build."""

# pylint: disable=protected-access
# pyright: basic
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pytest
from docker.models.images import Image
from mock import MagicMock
from pydantic import ValidationError

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from runway.cfngin.hooks.docker.hook_data import DockerHookData
from runway.cfngin.hooks.docker.image import build
from runway.cfngin.hooks.docker.image._build import (
    DockerImageBuildApiOptions,
    ImageBuildArgs,
)

from .....mock_docker.fake_api import FAKE_IMAGE_ID

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from .....factories import MockCFNginContext


MODULE = "runway.cfngin.hooks.docker.image._build"


@pytest.fixture(scope="function")
def tmp_dockerfile(cd_tmp_path: Path) -> Path:
    """Create temporary Dockerfile."""
    dockerfile = cd_tmp_path / "Dockerfile"
    dockerfile.touch()
    return dockerfile


def test_build(
    cfngin_context: MockCFNginContext, mocker: MockerFixture, tmp_path: Path
) -> None:
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


class TestDockerImageBuildApiOptions:
    """Test runway.cfngin.hooks.docker.image._build.DockerImageBuildApiOptions."""

    def test_field_defaults(self) -> None:
        """Test field defaults."""
        obj = DockerImageBuildApiOptions()
        assert not obj.buildargs and isinstance(obj.buildargs, dict)
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


@pytest.mark.usefixtures("tmp_dockerfile")
class TestImageBuildArgs:
    """Test runway.cfngin.hooks.docker.image._build.ImageBuildArgs."""

    @pytest.mark.parametrize(
        "repo, tag, expected",
        [(None, None, None), ("foo", None, "foo"), ("foo", "bar", "bar")],
    )
    def test__set_docker_dict(
        self,
        expected: Optional[str],
        repo: Optional[str],
        tag: Optional[str],
        tmp_path: Path,
    ) -> None:
        """Test _set_docker."""
        assert (
            ImageBuildArgs.parse_obj(
                {
                    "docker": {"tag": tag} if tag else {},
                    "path": tmp_path,
                    "repo": repo,
                }
            ).docker.tag
            == expected
        )

    @pytest.mark.parametrize(
        "repo, tag, expected",
        [(None, None, None), ("foo", None, "foo"), ("foo", "bar", "bar")],
    )
    def test__set_docker_model(
        self,
        expected: Optional[str],
        repo: Optional[str],
        tag: Optional[str],
        tmp_path: Path,
    ) -> None:
        """Test _set_docker."""
        assert (
            ImageBuildArgs(
                docker=DockerImageBuildApiOptions(tag=tag),
                path=tmp_path,
                repo=repo,
            ).docker.tag
            == expected
        )

    def test__set_ecr_repo_from_dict(self, tmp_path: Path) -> None:
        """Test _set_ecr_repo from Dict."""
        args = {
            "repo_name": "foo",
            "account_id": "123",
            "registry_alias": "bar",
            "aws_region": "us-west-2",
        }
        obj = ImageBuildArgs.parse_obj({"path": tmp_path, "ecr_repo": args})
        assert obj.ecr_repo
        assert obj.ecr_repo.name == args["repo_name"]
        assert obj.ecr_repo.registry.account_id == args["account_id"]
        assert obj.ecr_repo.registry.alias == args["registry_alias"]
        assert obj.ecr_repo.registry.region == args["aws_region"]

    def test__set_repo(self, tmp_path: Path) -> None:
        """Test _set_repo."""
        assert ImageBuildArgs(path=tmp_path, repo="something").repo == "something"

    def test__set_repo_ecr(self, tmp_path: Path) -> None:
        """Test _set_repo ECR."""
        repo = ElasticContainerRegistryRepository(
            repo_name="test",
            registry=ElasticContainerRegistry(
                account_id="123456789012", aws_region="us-east-1"
            ),
        )
        assert ImageBuildArgs(path=tmp_path, ecr_repo=repo).repo == repo.fqn

    def test__validate_dockerfile_raise_value_error(self, tmp_path: Path) -> None:
        """Test _validate_dockerfile raise ValueError."""
        with pytest.raises(ValidationError) as excinfo:
            assert ImageBuildArgs(dockerfile="invalid", path=tmp_path, repo="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("dockerfile",)
        assert errors[0]["msg"].startswith(
            "Dockerfile does not exist at path provided: "
        )
