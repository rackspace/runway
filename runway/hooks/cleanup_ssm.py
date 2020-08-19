"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""
# pylint: disable=unused-argument
# TODO move to runway.cfngin.hooks on next major release
import logging

LOGGER = logging.getLogger(__name__)


def delete_param(context, provider, **kwargs):
    """Delete SSM parameter."""
    parameter_name = kwargs.get("parameter_name")
    if not parameter_name:
        raise ValueError("Must specify `parameter_name` for delete_param hook.")

    session = context.get_session()
    ssm_client = session.client("ssm")

    try:
        ssm_client.delete_parameter(Name=parameter_name)
    except ssm_client.exceptions.ParameterNotFound:
        LOGGER.info('parameter "%s" does not exist', parameter_name)
    return True
