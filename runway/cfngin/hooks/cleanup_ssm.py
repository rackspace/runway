"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...utils import BaseModel

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class DeleteParamHookArgs(BaseModel):
    """Hook arguments for ``delete_param``."""

    parameter_name: str
    """Name of the bucket to purge."""


def delete_param(context: CfnginContext, *__args: Any, **kwargs: Any) -> bool:
    """Delete SSM parameter."""
    args = DeleteParamHookArgs.model_validate(kwargs)

    session = context.get_session()
    ssm_client = session.client("ssm")

    try:
        ssm_client.delete_parameter(Name=args.parameter_name)
    except ssm_client.exceptions.ParameterNotFound:
        LOGGER.info('parameter "%s" does not exist', args.parameter_name)
    return True
