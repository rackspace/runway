"""Pytest fixtures and plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from botocore.stub import Stubber
    from mypy_boto3_ssm.client import SSMClient

    from ....factories import MockCFNginContext


@pytest.fixture(scope="function")
def ssm_client(cfngin_context: MockCFNginContext, ssm_stubber: Stubber) -> SSMClient:
    """Create SSM client."""
    return cast("SSMClient", cfngin_context.get_session().client("ssm"))


@pytest.fixture(scope="function")
def ssm_stubber(cfngin_context: MockCFNginContext) -> Stubber:
    """Create SSM stubber."""
    return cfngin_context.add_stubber("ssm")
