"""AWS IAM hook."""
# pylint: disable=unused-argument
import copy
import logging

from awacs import ecs
from awacs.aws import Allow, Policy, Statement
from awacs.helpers.trust import get_ecs_assumerole_policy
from botocore.exceptions import ClientError
from six.moves import input

from ..session_cache import get_session
from . import utils

LOGGER = logging.getLogger(__name__)


def create_ecs_service_role(provider, context, **kwargs):
    """Create ecsServieRole, which has to be named exactly that currently.

    http://docs.aws.amazon.com/AmazonECS/latest/developerguide/IAM_policies.html#service_IAM_role

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance. (passed in by CFNgin)
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        role_name (str): Name of the role to create.
            (*default: ecsServiceRole*)

    Returns:
        bool: Whether or not the hook succeeded.

    """
    role_name = kwargs.get("role_name", "ecsServiceRole")
    client = get_session(provider.region).client('iam')

    try:
        client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=get_ecs_assumerole_policy().to_json()
        )
    except ClientError as err:
        if "already exists" in str(err):
            pass
        else:
            raise

    policy = Policy(
        Version='2012-10-17',
        Statement=[
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[ecs.CreateCluster, ecs.DeregisterContainerInstance,
                        ecs.DiscoverPollEndpoint, ecs.Poll,
                        ecs.Action("Submit*")]
            )
        ])
    client.put_role_policy(
        RoleName=role_name,
        PolicyName="AmazonEC2ContainerServiceRolePolicy",
        PolicyDocument=policy.to_json()
    )
    return True


def _get_cert_arn_from_response(response):
    result = copy.deepcopy(response)
    # GET response returns this extra key
    if "ServerCertificate" in response:
        result = response["ServerCertificate"]
    return result["ServerCertificateMetadata"]["Arn"]


def _get_cert_contents(kwargs):
    """Build parameters with server cert file contents.

    Args:
        kwargs (Dict[str, Any]): The keyword args passed to
            ensure_server_cert_exists, optionally containing the paths to the
            cert, key and chain files.

    Returns:
        Dict[str, Any]: A dictionary containing the appropriate parameters
            to supply to upload_server_certificate. An empty dictionary if
            there is a problem.

    """
    paths = {
        "certificate": kwargs.get("path_to_certificate"),
        "private_key": kwargs.get("path_to_private_key"),
        "chain": kwargs.get("path_to_chain"),
    }

    for key, value in paths.items():
        if value is not None:
            continue

        path = input("Path to %s (skip): " % (key,))
        if path == "skip" or not path.strip():
            continue

        paths[key] = path

    parameters = {
        "ServerCertificateName": kwargs.get("cert_name"),
    }

    for key, path in paths.items():
        if not path:
            continue

        # Allow passing of file like object for tests
        try:
            contents = path.read()
        except AttributeError:
            with open(utils.full_path(path)) as read_file:
                contents = read_file.read()

        if key == "certificate":
            parameters["CertificateBody"] = contents
        elif key == "private_key":
            parameters["PrivateKey"] = contents
        elif key == "chain":
            parameters["CertificateChain"] = contents

    return parameters


def ensure_server_cert_exists(provider, context, **kwargs):
    """Ensure server cert exists.

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance. (passed in by CFNgin)
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        cert_name (str): Name of the certificate that should exist.
        prompt (bool): Whether to prompt to upload a certificate if one does
            not exist. (*default:* ``True``)

    Returns:
        Dict[str, str]: Dict containing ``status``, ``cert_name``, and
            ``cert_arn``.

    """
    client = get_session(provider.region).client('iam')
    cert_name = kwargs["cert_name"]
    status = "unknown"
    try:
        response = client.get_server_certificate(
            ServerCertificateName=cert_name
        )
        cert_arn = _get_cert_arn_from_response(response)
        status = "exists"
        LOGGER.info("certificate exists: %s (%s)", cert_name, cert_arn)
    except ClientError:
        if kwargs.get("prompt", True):
            upload = input(
                "Certificate '%s' wasn't found. Upload it now? (yes/no) " % (
                    cert_name,
                )
            )
            if upload != "yes":
                return False

        parameters = _get_cert_contents(kwargs)
        if not parameters:
            return False
        response = client.upload_server_certificate(**parameters)
        cert_arn = _get_cert_arn_from_response(response)
        status = "uploaded"
        LOGGER.info(
            "uploaded certificate: %s (%s)",
            cert_name,
            cert_arn,
        )

    return {
        "status": status,
        "cert_name": cert_name,
        "cert_arn": cert_arn,
    }
