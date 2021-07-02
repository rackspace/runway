"""Execute the AWS CLI update-kubeconfig command."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

from runway.cfngin.lookups.handlers.output import OutputLookup
from runway.utils import which

if TYPE_CHECKING:
    from runway.context import CfnginContext

LOGGER = logging.getLogger(__name__)


def aws_eks_update_kubeconfig(context: CfnginContext, **kwargs: Any) -> bool:
    """Execute the aws cli eks update-kubeconfig command.

    Args:
        context: Context object.

    Returns:
        boolean for whether or not the hook succeeded

    """
    if kwargs.get("cluster-name"):
        eks_cluster_name = kwargs["cluster-name"]
    else:
        eks_cluster_name = OutputLookup.handle(
            f"{kwargs['stack']}::EksClusterName", context=context
        )
    LOGGER.info("writing kubeconfig...")
    subprocess.check_output(
        ["aws", "eks", "update-kubeconfig", "--name", eks_cluster_name]
    )
    LOGGER.info("kubeconfig written successfully...")

    # The newly-generated kubeconfig will have introduced a dependency on the
    # awscli. This is fine if a recent version is installed, or it's invoked
    # in a virtualenv with runway
    if not os.environ.get("PIPENV_ACTIVE") and (
        not os.environ.get("VIRTUAL_ENV") and not which("aws")
    ):
        print("", file=sys.stderr)  # noqa: T001
        print(  # noqa: T001
            "Warning: the generated kubeconfig uses the aws-cli for "
            "authentication, but it is not found in your environment. ",
            file=sys.stderr,
        )
    return True
