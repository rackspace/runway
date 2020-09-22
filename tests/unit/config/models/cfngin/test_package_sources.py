"""Test runway.config.models.cfngin._package_sources."""
# pylint: disable=no-self-use
from typing import Dict, List

import pytest
from pydantic import ValidationError

from runway.config.models.cfngin import (
    GitPackageSource,
    LocalPackageSource,
    PackageSources,
    S3PackageSource,
)


class TestGitPackageSource:
    """Test runway.config.models.cfngin._package_sources.GitPackageSource."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            GitPackageSource(invalid="something", uri="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = GitPackageSource(uri="something")
        assert not obj.branch
        assert not obj.commit
        assert obj.configs == []
        assert obj.paths == []
        assert not obj.tag
        assert obj.uri == "something"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            GitPackageSource()
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
        assert GitPackageSource.parse_obj(data)[ref["field"]] == ref["value"]

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
            GitPackageSource.parse_obj(data)
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("__root__",)
        assert errors[0]["msg"].startswith("only one of")


class TestLocalPackageSource:
    """Test runway.config.models.cfngin._package_sources.LocalPackageSource."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            LocalPackageSource(invalid="something", source="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = LocalPackageSource(source="something")
        assert obj.configs == []
        assert obj.paths == []
        assert obj.source == "something"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            LocalPackageSource()
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("source",)
        assert errors[0]["msg"] == "field required"


class TestPackageSources:
    """Test runway.config.models.cfngin._package_sources.PackageSources."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            PackageSources(invalid="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = PackageSources()
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
        obj: PackageSources = PackageSources.parse_obj(data)
        assert isinstance(obj.git[0], GitPackageSource)
        assert isinstance(obj.local[0], LocalPackageSource)
        assert isinstance(obj.s3[0], S3PackageSource)


class TestS3PackageSource:
    """Test runway.config.models.cfngin._package_sources.S3PackageSource."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            S3PackageSource(bucket="something", key="something", invalid="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            S3PackageSource()
        errors = excinfo.value.errors()
        assert len(errors) == 2
        assert errors[0]["loc"] == ("bucket",)
        assert errors[0]["msg"] == "field required"
        assert errors[1]["loc"] == ("key",)
        assert errors[1]["msg"] == "field required"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = S3PackageSource(bucket="bucket", key="something")
        assert obj.bucket == "bucket"
        assert obj.configs == []
        assert obj.key == "something"
        assert obj.paths == []
        assert not obj.requester_pays
        assert not obj.use_latest
