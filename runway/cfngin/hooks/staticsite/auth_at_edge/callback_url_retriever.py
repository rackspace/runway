"""Callback URL Retriever.

Dependency pre-hook responsible for ensuring correct
callback urls are retrieved or a temporary one is used in it's place.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...base import HookArgsBaseModel

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__)


class HookArgs(HookArgsBaseModel):
    """Hook arguments."""

    stack_name: str
    """The name of the stack to check against."""

    user_pool_arn: str | None = None
    """The ARN of the User Pool to check for a client."""


def get(context: CfnginContext, *_args: Any, **kwargs: Any) -> dict[str, Any]:
    """Retrieve the callback URLs for User Pool Client Creation.

    When the User Pool is created a Callback URL is required. During a post
    hook entitled ``client_updater`` these Callback URLs are updated to that
    of the Distribution. Before then we need to ensure that if a Client
    already exists that the URLs for that client are used to prevent any
    interruption of service during deploy.

    Arguments parsed by
    :class:`~runway.cfngin.hooks.staticsite.auth_at_edge.callback_url_retriever.HookArgs`.

    Args:
        context: The context instance.
        **kwargs: Arbitrary keyword arguments.

    """
    args = HookArgs.model_validate(kwargs)
    session = context.get_session()
    cloudformation_client = session.client("cloudformation")
    cognito_client = session.client("cognito-idp")

    context_dict = {"callback_urls": ["https://example.org"]}
    try:
        # Return the current stack if one exists
        stack_desc = cloudformation_client.describe_stacks(StackName=args.stack_name)
        # Get the client_id from the outputs
        outputs = stack_desc["Stacks"][0].get("Outputs", [])

        if args.user_pool_arn:
            user_pool_id = args.user_pool_arn.split("/")[-1:][0]
        else:
            user_pool_id = next(
                o["OutputValue"]
                for o in outputs
                if ("OutputKey" in o and "OutputValue" in o)
                and o["OutputKey"] == "AuthAtEdgeUserPoolId"
            )

        client_id = next(
            o["OutputValue"]
            for o in outputs
            if ("OutputKey" in o and "OutputValue" in o) and o["OutputKey"] == "AuthAtEdgeClient"
        )

        # Poll the user pool client information
        resp = cognito_client.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client_id)

        # Retrieve the callbacks
        callbacks = resp["UserPoolClient"].get("CallbackURLs")

        if callbacks:
            context_dict["callback_urls"] = callbacks
        return context_dict
    except Exception:  # noqa: BLE001
        return context_dict
