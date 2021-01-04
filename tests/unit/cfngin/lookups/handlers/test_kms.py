"""Tests for runway.cfngin.lookups.handlers.kms."""
# pylint: disable=no-self-use
from __future__ import annotations

import codecs
from typing import TYPE_CHECKING

from runway.cfngin.lookups.handlers.kms import KmsLookup

if TYPE_CHECKING:
    from ....factories import MockCFNginContext

SECRET = "my secret"


class TestKMSHandler:
    """Tests for runway.cfngin.lookups.handlers.kms.KmsLookup."""

    def test_kms_handler(self, cfngin_context: MockCFNginContext) -> None:
        """Test kms handler."""
        stubber = cfngin_context.add_stubber("kms")
        stubber.add_response(
            "decrypt",
            {"Plaintext": SECRET.encode()},
            {"CiphertextBlob": codecs.decode(SECRET.encode(), "base64")},
        )

        with stubber:
            assert KmsLookup.handle(SECRET, context=cfngin_context) == SECRET
            stubber.assert_no_pending_responses()

    def test_kms_handler_with_region(self, cfngin_context: MockCFNginContext) -> None:
        """Test kms handler with region."""
        region = "us-west-2"
        stubber = cfngin_context.add_stubber("kms", region=region)

        stubber.add_response(
            "decrypt",
            {"Plaintext": SECRET.encode()},
            {"CiphertextBlob": codecs.decode(SECRET.encode(), "base64")},
        )

        with stubber:
            assert (
                KmsLookup.handle(f"{region}@{SECRET}", context=cfngin_context) == SECRET
            )
            stubber.assert_no_pending_responses()
