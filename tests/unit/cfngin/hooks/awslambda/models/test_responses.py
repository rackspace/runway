"""Test runway.cfngin.hooks.awslambda.models.responses."""
# pylint: disable=no-self-use,protected-access
from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.cfngin.hooks.awslambda.models.responses import AwsLambdaHookDeployResponse


class TestAwsLambdaHookDeployResponse:
    """Test AwsLambdaHookDeployResponse."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            AwsLambdaHookDeployResponse(
                bucket_name="test-bucket",
                code_sha256="sha256",
                invalid=True,  # type: ignore
                object_key="key",
                runtime="test",
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"
