"""AWS account."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ....compat import cached_property

if TYPE_CHECKING:
    from collections.abc import Iterator

    import boto3
    from mypy_boto3_iam.type_defs import ListAccountAliasesResponseTypeDef

    from ....context import CfnginContext, RunwayContext


class AccountDetails:
    """AWS account details."""

    def __init__(self, context: CfnginContext | RunwayContext) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.

        """
        self.__ctx = context

    @cached_property
    def aliases(self) -> list[str]:
        """Get the aliases of the AWS account."""
        # Super overkill here using pagination when an account can only
        # have a single alias, but at least this implementation should be
        # future-proof.
        aliases: list[str] = []
        paginator = self.__session.client("iam").get_paginator("list_account_aliases")
        response_iterator = paginator.paginate()
        # NOTE (@ITProKyle): for some reason, pyright is not seeing `PageIterator` as a generic
        for page in cast("Iterator[ListAccountAliasesResponseTypeDef]", response_iterator):
            aliases.extend(page.get("AccountAliases", []))
        return aliases

    @cached_property
    def id(self) -> str:
        """Get the ID of the AWS account."""
        account_id = self.__session.client("sts").get_caller_identity().get("Account")
        if account_id:
            return account_id
        raise ValueError("get_caller_identity did not return Account")

    @cached_property
    def __session(self) -> boto3.Session:
        """Get a cached boto3 session.

        Session creation was moved out of class init to improve performance
        by only creating the session once it is needed.

        """
        return self.__ctx.get_session()
