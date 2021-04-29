"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


def delete_param(context: CfnginContext, *, parameter_name: str, **_: Any) -> bool:
    """Delete SSM parameter."""
    if not parameter_name:
        raise ValueError("Must specify `parameter_name` for delete_param hook.")

    session = context.get_session()
    ssm_client = session.client("ssm")

    try:
        ssm_client.delete_parameter(Name=parameter_name)
    except ssm_client.exceptions.ParameterNotFound:
        LOGGER.info('parameter "%s" does not exist', parameter_name)
    return True
