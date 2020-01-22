"""Execute the AWS CLI update-kubeconfig to generate your kubectl config."""
import os
import logging

from runway.cfngin.lookups.handlers.output import OutputLookup
from runway.cfngin.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def assumed_role_to_principle(assumed_role_arn):
    """Return role ARN from assumed role ARN."""
    arn_split = assumed_role_arn.split(':')
    arn_split[2] = 'iam'
    base_arn = ':'.join(arn_split[:5]) + ':role/'
    return base_arn + assumed_role_arn.split('/')[1]


def get_principal_arn(provider):
    """Return ARN of current session principle."""
    # looking up caller identity
    session = get_session(provider.region)
    sts_client = session.client('sts')
    caller_identity_arn = sts_client.get_caller_identity()['Arn']
    if caller_identity_arn.split(':')[2] == 'iam' and (
            caller_identity_arn.split(':')[5].startswith('user/')):
        return caller_identity_arn  # user arn
    return assumed_role_to_principle(caller_identity_arn)


def generate(provider, context, **kwargs):  # pylint: disable=W0613
    """Generate an EKS auth_map for worker connection.

    Args:
        provider (:class:`stacker.providers.base.BaseProvider`): provider
            instance
        context (:class:`stacker.context.Context`): context instance

    Returns: boolean for whether or not the hook succeeded.

    """
    overlay_path = os.path.join(*kwargs['path'])
    filename = os.path.join(overlay_path, kwargs['file'])
    if os.path.exists(filename):
        LOGGER.info("%s file present; skipping initial creation", filename)
        return True
    LOGGER.info("Creating auth_map at %s", filename)
    if not os.path.isdir(overlay_path):
        os.makedirs(overlay_path)
    principal_arn = get_principal_arn(provider)
    stack_name = kwargs['stack']
    node_instancerole_arn = OutputLookup.handle(
        "%s::NodeInstanceRoleArn" % stack_name,
        provider=provider,
        context=context
    )
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'aws-auth-cm.yaml'), 'r') as stream:
        aws_authmap_template = stream.read()
    with open(filename, 'w') as out:
        out.write(
            aws_authmap_template.replace(
                'INSTANCEROLEARNHERE',
                node_instancerole_arn
            ).replace(
                'ORIGINALPRINCIPALARNHERE',
                principal_arn
            )
        )
    return True


def remove(provider, context, **kwargs):  # pylint: disable=W0613
    """Remove an EKS auth_map for worker connection.

    For use after destroying a cluster.

    Args:
        provider (:class:`stacker.providers.base.BaseProvider`): provider
            instance
        context (:class:`stacker.context.Context`): context instance

    Returns: boolean for whether or not the hook succeeded.

    """
    overlay_path = os.path.join(*kwargs['path'])
    filename = os.path.join(overlay_path, kwargs['file'])
    if os.path.exists(filename):
        LOGGER.info("Removing %s...", filename)
        os.remove(filename)
    return True
