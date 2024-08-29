"""Test runway.cfngin.hooks.awslambda.models.responses."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.cfngin.hooks.awslambda.models.responses import AwsLambdaHookDeployResponse


class TestAwsLambdaHookDeployResponse:
    """Test AwsLambdaHookDeployResponse."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            AwsLambdaHookDeployResponse(
                bucket_name="test-bucket",
                code_sha256="sha256",
                invalid=True,  # type: ignore
                object_key="key",
                runtime="test",
            )
