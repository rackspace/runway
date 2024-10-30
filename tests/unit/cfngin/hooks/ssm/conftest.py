"""Pytest fixtures and plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from botocore.stub import Stubber
    from mypy_boto3_ssm.client import SSMClient

    from ....factories import MockCfnginContext


@pytest.fixture
def ssm_client(
    cfngin_context: MockCfnginContext, ssm_stubber: Stubber  # noqa: ARG001
) -> SSMClient:
    """Create SSM client."""
    return cfngin_context.get_session().client("ssm")


@pytest.fixture
def ssm_stubber(cfngin_context: MockCfnginContext) -> Stubber:
    """Create SSM stubber."""
    return cfngin_context.add_stubber("ssm")
