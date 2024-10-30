"""Test runway.cfngin.hooks.docker.data_models."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from docker.models.images import Image
from pydantic import ValidationError

from runway.cfngin.hooks.docker.data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from runway.utils import MutableMap

if TYPE_CHECKING:
    from ....factories import MockCfnginContext

MODULE = "runway.cfngin.hooks.docker.data_models"
MOCK_IMAGE_REPO = "dkr.test.com/image"
MOCK_IMAGE_PROPS = {
    "attrs": {"RepoTags": ["dkr.test.com/image:latest", "dkr.test.com/image:oldest"]},
    "id": "acb123",
    "short_id": "sha256:abc",
    "tags": ["dkr.test.com/image:latest", "dkr.test.com/image:oldest"],
}


@pytest.fixture
def mock_image() -> MagicMock:
    """Return a mock docker.models.images.Image."""
    return MagicMock(spec=Image, **MOCK_IMAGE_PROPS)


class TestDockerImage:
    """Test runway.cfngin.hooks.docker.data_models.DockerImage."""

    def test_id(self, mock_image: MagicMock) -> None:
        """Test id."""
        obj = DockerImage(image=mock_image)
        assert obj.id == MOCK_IMAGE_PROPS["id"]

    def test_repo(self, mock_image: MagicMock) -> None:
        """Test repo."""
        obj = DockerImage(image=mock_image)
        assert obj.repo == MOCK_IMAGE_REPO

    def test_sort_id(self, mock_image: MagicMock) -> None:
        """Test short_id."""
        obj = DockerImage(image=mock_image)
        assert obj.short_id == MOCK_IMAGE_PROPS["short_id"]

    def test_tags(self, mock_image: MagicMock) -> None:
        """Test tags."""
        assert DockerImage(image=mock_image).tags == ["latest", "oldest"]

    def test_uri(self, mock_image: MagicMock) -> None:
        """Test URI."""
        assert DockerImage(image=mock_image).uri == MutableMap(
            latest=MOCK_IMAGE_REPO + ":latest", oldest=MOCK_IMAGE_REPO + ":oldest"
        )


class TestElasticContainerRegistry:
    """Test runway.cfngin.hooks.docker._data_models.ElasticContainerRegistry."""

    def test_fqn_private(self) -> None:
        """Test fqn private."""
        obj = ElasticContainerRegistry(account_id="123456789012", aws_region="us-east-1")
        assert obj.fqn == "123456789012.dkr.ecr.us-east-1.amazonaws.com/"

    def test_fqn_public(self) -> None:
        """Test fqn public."""
        obj = ElasticContainerRegistry(alias="test")
        assert obj.fqn == "public.ecr.aws/test/"

    def test_init_default(self, cfngin_context: MockCfnginContext) -> None:
        """Test init default values."""
        account_id = "123456789012"
        sts_stubber = cfngin_context.add_stubber("sts")
        sts_stubber.add_response(
            "get_caller_identity",
            {
                "UserId": "str",
                "Account": account_id,
                "Arn": "arn:aws:iam:::user/test-user",
            },
        )

        with sts_stubber:
            obj = ElasticContainerRegistry.model_validate({"context": cfngin_context})
        sts_stubber.assert_no_pending_responses()
        assert obj.account_id == account_id
        assert obj.alias is None
        assert obj.region == cfngin_context.env.aws_region
        assert not obj.public

    def test_init_no_context(self) -> None:
        """Test init with no context."""
        with pytest.raises(ValidationError, match="context is required to resolve values"):
            ElasticContainerRegistry()

    def test_init_private(self) -> None:
        """Test init private."""
        account_id = "123456789012"
        region = "us-east-1"
        obj = ElasticContainerRegistry(account_id=account_id, aws_region=region)
        assert obj.account_id == account_id
        assert obj.alias is None
        assert obj.region == region
        assert not obj.public

    def test_init_public(self) -> None:
        """Test init public."""
        obj = ElasticContainerRegistry(alias="test")
        assert obj.account_id is None
        assert obj.alias == "test"
        assert obj.region is None
        assert obj.public


class TestElasticContainerRegistryRepository:
    """Test runway.cfngin.hooks.docker._data_models.ElasticContainerRegistryRepository."""

    def test_fqn(self, cfngin_context: MockCfnginContext) -> None:
        """Test init private."""
        account_id = "123456789012"
        region = "us-east-1"

        obj = ElasticContainerRegistryRepository(
            name="something",
            registry=ElasticContainerRegistry.model_validate(
                {"account_id": account_id, "aws_region": region, "context": cfngin_context}
            ),
        )
        assert obj.fqn == f"{obj.registry.fqn}{obj.name}"
