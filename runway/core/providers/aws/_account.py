"""AWS account."""
from typing import TYPE_CHECKING, List  # pylint: disable=W

from ....util import cached_property

if TYPE_CHECKING:
    from ....context import Context  # pylint: disable=W


class AccountDetails(object):
    """AWS account details."""

    def __init__(self, context):
        # type: (Context) -> None
        """Instantiate class.

        Args:
            context: Runway context object.

        """
        self.__ctx = context

    @cached_property
    def aliases(self):
        # type: () -> List[str]
        """Get the aliases of the AWS account.

        Returns:
            List[str]: Account aliases.

        """
        # Super overkill here using pagination when an account can only
        # have a single alias, but at least this implementation should be
        # future-proof.
        aliases = []
        paginator = self.__session.client("iam").get_paginator("list_account_aliases")
        response_iterator = paginator.paginate()
        for page in response_iterator:
            aliases.extend(page.get("AccountAliases", []))
        return aliases

    @cached_property
    def id(self):
        # type: () -> str
        """Get the ID of the AWS account.

        Returns:
            str: AWS account ID.

        """
        return self.__session.client("sts").get_caller_identity()["Account"]

    @cached_property
    def __session(self):
        """Get a cached boto3 session.

        Session creation was moved out of class init to improve performance
        by only creating the session once it is needed.

        """
        return self.__ctx.get_session()
