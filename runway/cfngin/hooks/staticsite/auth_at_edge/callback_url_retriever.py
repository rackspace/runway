"""Callback URL Retriever.

Dependency pre-hook responsible for ensuring correct
callback urls are retrieved or a temporary one is used in it's place.

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__)


def get(
    context: CfnginContext,
    *,
    stack_name: str,
    user_pool_arn: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Retrieve the callback URLs for User Pool Client Creation.

    When the User Pool is created a Callback URL is required. During a post
    hook entitled ``client_updater`` these Callback URLs are updated to that
    of the Distribution. Before then we need to ensure that if a Client
    already exists that the URLs for that client are used to prevent any
    interuption of service during deploy.

    Args:
        context: The context instance.
        stack_name: The name of the stack to check against.
        user_pool_arn: The ARN of the User Pool to check for a client.

    """
    session = context.get_session()
    cloudformation_client = session.client("cloudformation")
    cognito_client = session.client("cognito-idp")

    context_dict = {"callback_urls": ["https://example.org"]}
    try:
        # Return the current stack if one exists
        stack_desc = cloudformation_client.describe_stacks(StackName=stack_name)
        # Get the client_id from the outputs
        outputs = stack_desc["Stacks"][0]["Outputs"]

        if user_pool_arn:
            user_pool_id = user_pool_arn.split("/")[-1:][0]
        else:
            user_pool_id = [
                o["OutputValue"]
                for o in outputs
                if o["OutputKey"] == "AuthAtEdgeUserPoolId"
            ][0]

        client_id = [
            o["OutputValue"] for o in outputs if o["OutputKey"] == "AuthAtEdgeClient"
        ][0]

        # Poll the user pool client information
        resp = cognito_client.describe_user_pool_client(
            UserPoolId=user_pool_id, ClientId=client_id
        )

        # Retrieve the callbacks
        callbacks = resp["UserPoolClient"]["CallbackURLs"]

        if callbacks:
            context_dict["callback_urls"] = callbacks
        return context_dict
    except Exception:  # pylint: disable=broad-except
        return context_dict
