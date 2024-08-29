"""Test runway.config.models.runway._assume_role."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.config.models.runway._assume_role import RunwayAssumeRoleDefinitionModel


class TestRunwayAssumeRoleDefinitionModel:
    """Test RunwayAssumeRoleDefinitionModel."""

    @pytest.mark.parametrize("arn", ["null", "none", "None", "undefined"])
    def test_convert_arn_null_value(self, arn: str) -> None:
        """Test _convert_arn_null_value."""
        assert not RunwayAssumeRoleDefinitionModel(arn=arn).arn

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            RunwayAssumeRoleDefinitionModel.model_validate({"invalid": "val"})

    def test_field_defaults(self) -> None:
        """Test field values."""
        obj = RunwayAssumeRoleDefinitionModel()
        assert not obj.arn
        assert obj.duration == 3600
        assert not obj.post_deploy_env_revert
        assert obj.session_name == "runway"

    def test_fields(self) -> None:
        """Test fields."""
        data = {
            "arn": "test-arn",
            "duration": 900,
            "post_deploy_env_revert": True,
            "session_name": "test-session",
        }
        obj = RunwayAssumeRoleDefinitionModel.model_validate(data)
        assert obj.arn == data["arn"]
        assert obj.duration == data["duration"]
        assert obj.post_deploy_env_revert == data["post_deploy_env_revert"]
        assert obj.session_name == data["session_name"]

    def test_string_duration(self) -> None:
        """Test duration defined as a string."""
        with pytest.raises(
            ValidationError,
            match="duration\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayAssumeRoleDefinitionModel(duration="something")

    def test_string_duration_lookup(self) -> None:
        """Test duration defined as a lookup string."""
        value = "${var something}"
        obj = RunwayAssumeRoleDefinitionModel(duration=value)
        assert obj.duration == value

    @pytest.mark.parametrize("duration", [900, 3600, 43_200])
    def test_validate_duration(self, duration: int) -> None:
        """Test _validate_duration."""
        assert RunwayAssumeRoleDefinitionModel(duration=duration).duration == duration

    @pytest.mark.parametrize("duration", [899, 43_201])
    def test_validate_duration_invalid(self, duration: int) -> None:
        """Test _validate_duration."""
        with pytest.raises(ValidationError, match="duration"):
            RunwayAssumeRoleDefinitionModel(duration=duration)
