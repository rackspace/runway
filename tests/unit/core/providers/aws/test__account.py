"""Test runway.core.providers.aws._account."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.core.providers.aws import AccountDetails

if TYPE_CHECKING:
    from ....factories import MockRunwayContext


class TestAccountDetails:
    """Test runway.core.providers.aws._account.AccountDetails."""

    def test_aliases(self, runway_context: MockRunwayContext) -> None:
        """Test aliases."""
        aliases = ["test", "runway-test"]
        stubber = runway_context.add_stubber("iam")
        stubber.add_response(
            "list_account_aliases", {"AccountAliases": aliases, "IsTruncated": False}
        )
        account = AccountDetails(runway_context)
        with stubber:
            assert account.aliases == aliases

    def test_id(self, runway_context: MockRunwayContext) -> None:
        """Test id."""
        account_id = "123456789012"
        arn = f"arn:aws:iam::{account_id}:user/test-user"
        stubber = runway_context.add_stubber("sts")
        stubber.add_response(
            "get_caller_identity",
            {"UserId": "test-user", "Account": account_id, "Arn": arn},
        )
        account = AccountDetails(runway_context)
        with stubber:
            assert account.id == account_id

    def test_id_raise_value_error(self, runway_context: MockRunwayContext) -> None:
        """Test id raise ValueError."""
        account_id = "123456789012"
        arn = f"arn:aws:iam::{account_id}:user/test-user"
        stubber = runway_context.add_stubber("sts")
        stubber.add_response(
            "get_caller_identity",
            {"UserId": "test-user", "Arn": arn},
        )
        account = AccountDetails(runway_context)
        with stubber, pytest.raises(ValueError, match="get_caller_identity did not return Account"):
            assert not account.id
