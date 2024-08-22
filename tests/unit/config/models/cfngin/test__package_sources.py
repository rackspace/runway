"""Test runway.config.models.cfngin._package_sources."""

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
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            CfnginPackageSourcesDefinitionModel.model_validate({"invalid": "val"})

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
            CfnginPackageSourcesDefinitionModel.model_validate(data)
        )
        assert isinstance(obj.git[0], GitCfnginPackageSourceDefinitionModel)
        assert isinstance(obj.local[0], LocalCfnginPackageSourceDefinitionModel)
        assert isinstance(obj.s3[0], S3CfnginPackageSourceDefinitionModel)


class TestGitCfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.GitCfnginPackageSourceDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            GitCfnginPackageSourceDefinitionModel(
                invalid="something",  # type: ignore
                uri="something",
            )

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
        with pytest.raises(ValidationError, match="uri\n  Field required"):
            GitCfnginPackageSourceDefinitionModel.model_validate({})

    @pytest.mark.parametrize(
        "ref",
        [
            {"field": "branch", "value": "master"},
            {"field": "commit", "value": "1234"},
            {"field": "tag", "value": "v1.0.0"},
        ],
    )
    def test_validate_one_ref(self, ref: dict[str, str]) -> None:
        """Test _validate_one_ref."""
        data = {"uri": "something", ref["field"]: ref["value"]}
        assert (
            GitCfnginPackageSourceDefinitionModel.model_validate(data)[ref["field"]] == ref["value"]
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
    def test_validate_one_ref_invalid(self, refs: list[dict[str, str]]) -> None:
        """Test _validate_one_ref invalid values."""
        data = {"uri": "something", **{ref["field"]: ref["value"] for ref in refs}}
        with pytest.raises(
            ValidationError,
            match=r"1 validation error.*\n  Value error, only one of \['branch', 'commit', 'tag'\] can be defined",
        ):
            GitCfnginPackageSourceDefinitionModel.model_validate(data)


class TestLocalCfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.LocalCfnginPackageSourceDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            LocalCfnginPackageSourceDefinitionModel(
                invalid="something",  # type: ignore
                source="something",
            )

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = LocalCfnginPackageSourceDefinitionModel(source="something")
        assert obj.configs == []
        assert obj.paths == []
        assert obj.source == "something"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError, match="source\n  Field required"):
            LocalCfnginPackageSourceDefinitionModel.model_validate({})


class TestS3CfnginPackageSourceDefinitionModel:
    """Test runway.config.models.cfngin._package_sources.S3CfnginPackageSourceDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            S3CfnginPackageSourceDefinitionModel(
                bucket="something",
                key="something",
                invalid="something",  # type: ignore
            )

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(
            ValidationError,
            match="2 validation errors.*\nbucket\n  Field required.*\n.*\nkey\n  Field required",
        ):
            S3CfnginPackageSourceDefinitionModel.model_validate({})

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = S3CfnginPackageSourceDefinitionModel(bucket="bucket", key="something")
        assert obj.bucket == "bucket"
        assert obj.configs == []
        assert obj.key == "something"
        assert obj.paths == []
        assert not obj.requester_pays
        assert obj.use_latest
