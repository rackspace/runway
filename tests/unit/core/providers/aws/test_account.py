"""Test runway.core.providers.aws._account."""
# pylint: disable=no-self-use
from runway.core.providers.aws import AccountDetails


class TestAccountDetails(object):
    """Test runway.core.providers.aws._account.AccountDetails."""

    def test_aliases(self, runway_context):
        """Test aliases."""
        aliases = ["test", "runway-test"]
        stubber = runway_context.add_stubber("iam")
        stubber.add_response(
            "list_account_aliases", {"AccountAliases": aliases, "IsTruncated": False}
        )
        account = AccountDetails(runway_context)
        with stubber:
            assert account.aliases == aliases

    def test_id(self, runway_context):
        """Test id."""
        account_id = "123456789012"
        arn = "arn:aws:iam::{}:user/test-user".format(account_id)
        stubber = runway_context.add_stubber("sts")
        stubber.add_response(
            "get_caller_identity",
            {"UserId": "test-user", "Account": account_id, "Arn": arn},
        )
        account = AccountDetails(runway_context)
        with stubber:
            assert account.id == account_id
