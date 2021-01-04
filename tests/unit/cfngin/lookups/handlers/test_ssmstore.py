"""Tests for runway.cfngin.lookups.handlers.ssmstore."""
# pylint: disable=no-self-use
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.cfngin.lookups.handlers.ssmstore import SsmstoreLookup

if TYPE_CHECKING:
    from ....factories import MockCFNginContext


SSM_KEY = "ssmkey"
SSM_VALUE = "ssmvalue"

EXPECTED_PARAMS = {"Names": [SSM_KEY], "WithDecryption": True}
GET_PARAMETER_RESPONSE = {
    "Parameters": [{"Name": SSM_KEY, "Type": "String", "Value": SSM_VALUE}],
    "InvalidParameters": ["invalid_ssm_param"],
}
INVALID_GET_PARAMETER_RESPONSE = {"InvalidParameters": [SSM_KEY]}


class TestSSMStoreHandler:
    """Tests for runway.cfngin.lookups.handlers.ssmstore.SsmstoreLookup."""

    def test_ssmstore_handler(self, cfngin_context: MockCFNginContext) -> None:
        """Test ssmstore handler."""
        stubber = cfngin_context.add_stubber("ssm")
        stubber.add_response("get_parameters", GET_PARAMETER_RESPONSE, EXPECTED_PARAMS)
        with stubber:
            assert SsmstoreLookup.handle(SSM_KEY, context=cfngin_context) == SSM_VALUE

    def test_ssmstore_invalid_value_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test ssmstore invalid value handler."""
        stubber = cfngin_context.add_stubber("ssm")
        stubber.add_response(
            "get_parameters", INVALID_GET_PARAMETER_RESPONSE, EXPECTED_PARAMS
        )
        with stubber, pytest.raises(ValueError):
            SsmstoreLookup.handle(SSM_KEY, context=cfngin_context)

    def test_ssmstore_handler_with_region(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test ssmstore handler with region."""
        region = "us-west-2"
        stubber = cfngin_context.add_stubber("ssm", region=region)
        stubber.add_response("get_parameters", GET_PARAMETER_RESPONSE, EXPECTED_PARAMS)
        with stubber:
            assert (
                SsmstoreLookup.handle(f"{region}@{SSM_KEY}", context=cfngin_context)
                == SSM_VALUE
            )
