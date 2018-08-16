"""Stacker hook for cleaning up resources prior to CFN stack deletion."""

import logging

from stacker.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def delete_param(context, provider, **kwargs):  # noqa pylint: disable=unused-argument
    """Delete SSM parameter."""
    parameter_name = kwargs.get('parameter_name')
    if not parameter_name:
        raise ValueError('Must specify `parameter_name` for delete_param '
                         'hook.')

    session = get_session(provider.region)
    ssm_client = session.client('ssm')

    try:
        ssm_client.delete_parameter(Name=parameter_name)
    except ssm_client.exceptions.ParameterNotFound:
        LOGGER.info("%s parameter appears to have already been deleted...",
                    parameter_name)
    return True
