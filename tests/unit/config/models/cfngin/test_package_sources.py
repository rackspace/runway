"""Test runway.config.models.cfngin._package_sources."""

# pyright: basic
from typing import Dict, List

import pytest
from pydantic import ValidationError

from runway.config.models.cfngin import (
    CfnginPackageSourcesDefinitionModel,
    GitCfnginPackageSourceDefinitionModel,
    LocalCfnginPackageSourceDefinitionModel,
    S3CfnginPackageSourceDefinitionModel,
)


class TestCfnginPackageSourcesDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.CfnginPackageSourcesDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            CfnginPackageSourcesDefinitionModel.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = CfnginPackageSourcesDefinitionModel()
        assert obj.git == []
        assert obj.local == []
        assert obj.s3 == []

    def test_fields(self) -> None:
        """Test fields."""
        data = {
            "git": [{"uri": "something"}],
            "local": [{"source": "something"}],
            "s3": [{"bucket": "bucket", "key": "something"}],
        }
        obj: CfnginPackageSourcesDefinitionModel = (
            CfnginPackageSourcesDefinitionModel.parse_obj(data)
        )
        assert isinstance(obj.git[0], GitCfnginPackageSourceDefinitionModel)
        assert isinstance(obj.local[0], LocalCfnginPackageSourceDefinitionModel)
        assert isinstance(obj.s3[0], S3CfnginPackageSourceDefinitionModel)


class TestGitCfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.GitCfnginPackageSourceDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            GitCfnginPackageSourceDefinitionModel(
                invalid="something",  # type: ignore
                uri="something",
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = GitCfnginPackageSourceDefinitionModel(uri="something")
        assert not obj.branch
        assert not obj.commit
        assert obj.configs == []
        assert obj.paths == []
        assert not obj.tag
        assert obj.uri == "something"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            GitCfnginPackageSourceDefinitionModel()  # type: ignore
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("uri",)
        assert errors[0]["msg"] == "field required"

    @pytest.mark.parametrize(
        "ref",
        [
            {"field": "branch", "value": "master"},
            {"field": "commit", "value": "1234"},
            {"field": "tag", "value": "v1.0.0"},
        ],
    )
    def test_validate_one_ref(self, ref: Dict[str, str]) -> None:
        """Test _validate_one_ref."""
        data = {"uri": "something", ref["field"]: ref["value"]}
        assert (
            GitCfnginPackageSourceDefinitionModel.parse_obj(data)[ref["field"]]
            == ref["value"]
        )

    @pytest.mark.parametrize(
        "refs",
        [
            [
                {"field": "branch", "value": "master"},
                {"field": "commit", "value": "1234"},
            ],
            [
                {"field": "branch", "value": "master"},
                {"field": "tag", "value": "v1.0.0"},
            ],
            [
                {"field": "commit", "value": "1234"},
                {"field": "tag", "value": "v1.0.0"},
            ],
            [
                {"field": "branch", "value": "master"},
                {"field": "commit", "value": "1234"},
                {"field": "tag", "value": "v1.0.0"},
            ],
        ],
    )
    def test_validate_one_ref_invalid(self, refs: List[Dict[str, str]]) -> None:
        """Test _validate_one_ref invalid values."""
        data = {"uri": "something", **{ref["field"]: ref["value"] for ref in refs}}
        with pytest.raises(ValidationError) as excinfo:
            GitCfnginPackageSourceDefinitionModel.parse_obj(data)
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("__root__",)
        assert errors[0]["msg"].startswith("only one of")


class TestLocalCfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.LocalCfnginPackageSourceDefinitionModel."""  # noqa

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            LocalCfnginPackageSourceDefinitionModel(
                invalid="something",  # type: ignore
                source="something",
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = LocalCfnginPackageSourceDefinitionModel(source="something")
        assert obj.configs == []
        assert obj.paths == []
        assert obj.source == "something"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            LocalCfnginPackageSourceDefinitionModel()  # type: ignore
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("source",)
        assert errors[0]["msg"] == "field required"


class TestS3CfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.S3CfnginPackageSourceDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            S3CfnginPackageSourceDefinitionModel(
                bucket="something",
                key="something",
                invalid="something",  # type: ignore
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            S3CfnginPackageSourceDefinitionModel()  # type: ignore
        errors = excinfo.value.errors()
        assert len(errors) == 2
        assert errors[0]["loc"] == ("bucket",)
        assert errors[0]["msg"] == "field required"
        assert errors[1]["loc"] == ("key",)
        assert errors[1]["msg"] == "field required"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = S3CfnginPackageSourceDefinitionModel(bucket="bucket", key="something")
        assert obj.bucket == "bucket"
        assert obj.configs == []
        assert obj.key == "something"
        assert obj.paths == []
        assert not obj.requester_pays
        assert obj.use_latest
