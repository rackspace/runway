"""AWS IAM hook."""
from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any, Dict, Union, cast

from awacs import ecs
from awacs.aws import Allow, Policy, Statement
from awacs.helpers.trust import get_ecs_assumerole_policy
from botocore.exceptions import ClientError

from . import utils

if TYPE_CHECKING:
    from mypy_boto3_iam.type_defs import (
        GetServerCertificateResponseTypeDef,
        UploadServerCertificateResponseTypeDef,
    )

    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


def create_ecs_service_role(
    context: CfnginContext, *, role_name: str = "ecsServiceRole", **_: Any
) -> bool:
    """Create ecsServiceRole IAM role.

    https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using-service-linked-roles.html

    Args:
        context: Context instance. (passed in by CFNgin)
        role_name: Name of the role to create.

    """
    client = context.get_session().client("iam")

    try:
        client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=get_ecs_assumerole_policy().to_json(),
        )
    except ClientError as err:
        if "already exists" not in str(err):
            raise
    policy = Policy(
        Version="2012-10-17",
        Statement=[
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    ecs.CreateCluster,
                    ecs.DeregisterContainerInstance,
                    ecs.DiscoverPollEndpoint,
                    ecs.Poll,
                    ecs.Action("Submit*"),
                ],
            )
        ],
    )
    client.put_role_policy(
        RoleName=role_name,
        PolicyName="AmazonEC2ContainerServiceRolePolicy",
        PolicyDocument=policy.to_json(),
    )
    return True


def _get_cert_arn_from_response(
    response: Union[
        GetServerCertificateResponseTypeDef, UploadServerCertificateResponseTypeDef
    ]
) -> str:
    result = copy.deepcopy(response)
    # GET response returns this extra key
    if "ServerCertificate" in response:
        return cast("GetServerCertificateResponseTypeDef", result)["ServerCertificate"][
            "ServerCertificateMetadata"
        ]["Arn"]
    return (
        cast("UploadServerCertificateResponseTypeDef", result)
        .get("ServerCertificateMetadata", {})
        .get("Arn", "")
    )


def _get_cert_contents(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters with server cert file contents.

    Args:
        kwargs: The keyword args passed to ensure_server_cert_exists, optionally
            containing the paths to the cert, key and chain files.

    Returns:
        A dictionary containing the appropriate parameters to supply to
        upload_server_certificate. An empty dictionary if there is a problem.

    """
    paths = {
        "certificate": kwargs.get("path_to_certificate"),
        "private_key": kwargs.get("path_to_private_key"),
        "chain": kwargs.get("path_to_chain"),
    }

    for key, value in paths.items():
        if value is not None:
            continue

        path = input(f"Path to {key} (skip): ")
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
            with open(utils.full_path(path), encoding="utf-8") as read_file:
                contents = read_file.read()

        if key == "certificate":
            parameters["CertificateBody"] = contents
        elif key == "private_key":
            parameters["PrivateKey"] = contents
        elif key == "chain":
            parameters["CertificateChain"] = contents

    return parameters


def ensure_server_cert_exists(
    context: CfnginContext, *, cert_name: str, prompt: bool = True, **kwargs: Any
) -> Dict[str, str]:
    """Ensure server cert exists.

    Args:
        context: CFNgin context object.
        cert_name: Name of the certificate that should exist.
        prompt: Whether to prompt to upload a certificate if one does not exist.

    Returns:
        Dict containing ``status``, ``cert_name``, and ``cert_arn``.

    """
    client = context.get_session().client("iam")
    status = "unknown"
    try:
        response = client.get_server_certificate(ServerCertificateName=cert_name)
        cert_arn = _get_cert_arn_from_response(response)
        status = "exists"
        LOGGER.info("certificate exists: %s (%s)", cert_name, cert_arn)
    except ClientError:
        if prompt:
            upload = input(
                f"Certificate '{cert_name}' wasn't found. Upload it now? (yes/no) "
            )
            if upload != "yes":
                return {}

        parameters = _get_cert_contents(kwargs)
        if not parameters:
            return {}
        response = client.upload_server_certificate(**parameters)
        cert_arn = _get_cert_arn_from_response(response)
        status = "uploaded"
        LOGGER.info("uploaded certificate: %s (%s)", cert_name, cert_arn)

    return {
        "status": status,
        "cert_name": cert_name,
        "cert_arn": cert_arn,
    }
