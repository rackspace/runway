"""CFNgin prehook responsible for creation of Lambda@Edge functions."""
from __future__ import annotations

import logging
import os
import re
import secrets
import shutil
import tempfile
from distutils.dir_util import copy_tree
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ... import aws_lambda

if TYPE_CHECKING:
    from .....context import CfnginContext
    from ....providers.aws.default import Provider

# The functions associated with Auth@Edge
FUNCTIONS = ["check_auth", "refresh_auth", "parse_auth", "sign_out", "http_headers"]


LOGGER = logging.getLogger(__name__)


def write(  # pylint: disable=too-many-locals
    context: CfnginContext,
    *,
    bucket: str,
    client_id: str,
    cookie_settings: Dict[str, Any],
    http_headers: Dict[str, Any],
    nonce_signing_secret_param_name: str,
    oauth_scopes: List[str],
    provider: Provider,
    redirect_path_refresh: str,
    redirect_path_sign_in: str,
    redirect_path_sign_out: str,
    required_group: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Writes/Uploads the configured lambdas for Auth@Edge.

    Lambda@Edge does not have the ability to allow Environment variables
    at the time of this writing. In order to configure our lambdas with
    dynamic variables we first will go through and update a "shared" template
    with all of the configuration elements and add that to a temporary
    folder along with each of the individual Lambda@Edge functions. This
    temporary folder is then used with the CFNgin awsLambda hook to build
    the functions.

    Args:
        context: The CFNgin context.
        bucket: S3 bucket name.
        client_id: The ID of the Cognito User Pool Client.
        cookie_settings: The settings for our customized cookies.
        http_headers: The additional headers added to our requests.
        nonce_signing_secret_param_name: SSM param name to store nonce
            signing secret.
        oauth_scopes: The validation scopes for our OAuth requests.
        provider: The CFNgin provider.
        redirect_path_refresh: The URL path for authorization refresh
            redirect (Correlates to the refresh auth lambda).
        redirect_path_sign_in: The URL path to be redirected to after
            sign in (Correlates to the parse auth lambda).
        redirect_path_sign_out: The URL path to be redirected to after
            sign out (Correlates to the root to be asked to resigning).
        required_group: Optional User Pool group to which access should be
            restricted.

    """
    cognito_domain = context.hook_data["aae_domain_updater"].get("domain")
    config = {
        "client_id": client_id,
        "cognito_auth_domain": cognito_domain,
        "cookie_settings": cookie_settings,
        "http_headers": http_headers,
        "oauth_scopes": oauth_scopes,
        "redirect_path_auth_refresh": redirect_path_refresh,
        "redirect_path_sign_in": redirect_path_sign_in,
        "redirect_path_sign_out": redirect_path_sign_out,
        "required_group": required_group,
        "user_pool_id": context.hook_data["aae_user_pool_id_retriever"]["id"],
        "nonce_signing_secret": get_nonce_signing_secret(
            nonce_signing_secret_param_name, context
        ),
    }

    # Shared file that contains the method called for configuration data
    path = os.path.join(os.path.dirname(__file__), "templates", "shared.py")
    context_dict: Dict[str, Any] = {}

    with open(path, encoding="utf-8") as file_:
        # Dynamically replace our configuration values
        # in the shared.py template file with actual
        # calculated values
        shared = re.sub(
            r"{.+?(})$", str(config), file_.read(), 1, flags=re.DOTALL | re.MULTILINE
        )

        filedir, temppath = mkstemp()

        # Save the file to a temp path
        with open(temppath, "w", encoding="utf-8") as tmp:
            tmp.write(shared)
            config = temppath
        os.close(filedir)

        # Get all of the different Auth@Edge functions
        for handler in FUNCTIONS:
            # Create a temporary folder
            dirpath = tempfile.mkdtemp()

            # Copy the template code for the specific Lambda function
            # to the temporary folder
            copy_tree(
                os.path.join(os.path.dirname(__file__), "templates", handler), dirpath
            )

            # Save our dynamic configuration shared file to the
            # temporary folder
            with open(config, encoding="utf-8") as shared:
                raw = shared.read()
                filename = "shared.py"
                with open(os.path.join(dirpath, filename), "wb") as newfile:
                    newfile.write(raw.encode())

            # Copy the shared jose-dependent util module to the temporary folder
            shutil.copyfile(
                os.path.join(os.path.dirname(__file__), "templates", "shared_jose.py"),
                os.path.join(dirpath, "shared_jose.py"),
            )

            # Upload our temporary folder to our S3 bucket for
            # Lambda use
            lamb = aws_lambda.upload_lambda_functions(
                context,
                provider,
                bucket=bucket,
                functions={
                    handler: {
                        "path": dirpath,
                        "python_dontwritebytecode": True,
                        "python_exclude_bin_dir": True,
                        "python_exclude_setuptools_dirs": True,
                    }
                },
            )

            # Add the lambda code reference to our context_dict
            context_dict.update(lamb)

    return context_dict


def get_nonce_signing_secret(param_name: str, context: CfnginContext) -> str:
    """Retrieve signing secret, generating & storing it first if not present."""
    session = context.get_session()
    ssm_client = session.client("ssm")
    try:
        response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        secret = random_key(16)
        ssm_client.put_parameter(
            Description="Auth@Edge nonce signing secret",
            Name=param_name,
            Type="String",
            Value=secret,
        )
        return secret


def random_key(length: int = 16) -> str:
    """Generate a random key of specified length from the allowed secret characters.

    Args:
        length: The length of the random key.

    """
    secret_allowed_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    )
    return "".join(secrets.choice(secret_allowed_chars) for _ in range(length))
