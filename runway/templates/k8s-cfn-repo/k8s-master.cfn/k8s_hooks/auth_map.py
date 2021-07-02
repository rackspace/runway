"""Execute the AWS CLI update-kubeconfig to generate your kubectl config."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, List

from runway.cfngin.lookups.handlers.output import OutputLookup

if TYPE_CHECKING:
    from runway.context import CfnginContext

LOGGER = logging.getLogger(__name__)


def assumed_role_to_principle(assumed_role_arn: str) -> str:
    """Return role ARN from assumed role ARN."""
    arn_split = assumed_role_arn.split(":")
    arn_split[2] = "iam"
    base_arn = ":".join(arn_split[:5]) + ":role/"
    return base_arn + assumed_role_arn.split("/")[1]


def get_principal_arn(context: CfnginContext) -> str:
    """Return ARN of current session principle."""
    # looking up caller identity
    session = context.get_session()
    sts_client = session.client("sts")
    caller_identity_arn = sts_client.get_caller_identity().get("Arn", "")
    if caller_identity_arn.split(":")[2] == "iam" and (
        caller_identity_arn.split(":")[5].startswith("user/")
    ):
        return caller_identity_arn  # user arn
    return assumed_role_to_principle(caller_identity_arn)


def generate(
    context: CfnginContext, *, filename: str, path: List[str], stack: str, **_: Any
):
    """Generate an EKS auth_map for worker connection.

    Args:
        context: Context object.
        filename: Name of the file.
        path: Path to the file.
        stack: Stack definition.

    Returns:
        boolean for whether or not the hook succeeded

    """
    overlay_path = Path(*path)
    file_path = overlay_path / filename
    if os.path.exists(filename):
        LOGGER.info("%s file present; skipping initial creation", file_path)
        return True
    LOGGER.info("Creating auth_map at %s", file_path)
    overlay_path.mkdir(parents=True, exist_ok=True)
    principal_arn = get_principal_arn(context)
    node_instancerole_arn = OutputLookup.handle(
        f"{stack}::NodeInstanceRoleArn", context=context
    )
    aws_authmap_template = (Path(__file__).parent / "aws-auth-cm.yaml").read_text()
    file_path.write_text(
        aws_authmap_template.replace(
            "INSTANCEROLEARNHERE", node_instancerole_arn
        ).replace("ORIGINALPRINCIPALARNHERE", principal_arn)
    )
    return True


def remove(*, path: List[str], filename: str, **_: Any) -> bool:
    """Remove an EKS auth_map for worker connection.

    For use after destroying a cluster.

    Args:
        path: Path of the file.
        filename: Name of the file.

    Returns:
        boolean for whether or not the hook succeeded.

    """
    overlay_path = Path(*path)
    file_path = overlay_path / filename
    if file_path.is_file():
        LOGGER.info("Removing %s...", file_path)
        file_path.unlink()
    return True
