"""Tests for runway.cfngin.lookups.handlers.kms."""

# pyright: basic
from __future__ import annotations

import codecs
import string
from typing import TYPE_CHECKING

import pytest

from runway.cfngin.lookups.handlers.kms import KmsLookup

if TYPE_CHECKING:
    from ....factories import MockCFNginContext

SECRET = "my secret"


class TestKMSHandler:
    """Tests for runway.cfngin.lookups.handlers.kms.KmsLookup."""

    def test_handle(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle."""
        stubber = cfngin_context.add_stubber("kms")
        stubber.add_response(
            "decrypt",
            {"Plaintext": SECRET.encode()},
            {"CiphertextBlob": codecs.decode(SECRET.encode(), "base64")},
        )

        with stubber:
            assert KmsLookup.handle(SECRET, context=cfngin_context) == SECRET
            stubber.assert_no_pending_responses()

    @pytest.mark.parametrize(
        "template", ["${region}@${blob}", "${blob}::region=${region}"]
    )
    def test_handle_with_region(
        self, cfngin_context: MockCFNginContext, template: str
    ) -> None:
        """Test handle with region."""
        region = "us-west-2"
        query = string.Template(template).substitute({"blob": SECRET, "region": region})
        stubber = cfngin_context.add_stubber("kms", region=region)

        stubber.add_response(
            "decrypt",
            {"Plaintext": SECRET.encode()},
            {"CiphertextBlob": codecs.decode(SECRET.encode(), "base64")},
        )

        with stubber:
            assert KmsLookup.handle(query, context=cfngin_context) == SECRET
            stubber.assert_no_pending_responses()

    def test_legacy_parse(self) -> None:
        """Test legacy_parse."""
        assert KmsLookup.legacy_parse("us-east-1@foo") == (
            "foo",
            {"region": "us-east-1"},
        )
