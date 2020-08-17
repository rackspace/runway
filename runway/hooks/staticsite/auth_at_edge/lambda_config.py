"""CFNgin prehook responsible for creation of Lambda@Edge functions."""
import logging
import os
import re
import tempfile
from distutils.dir_util import copy_tree  # pylint: disable=E
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, Dict, Optional  # pylint: disable=W

from ....cfngin.hooks import aws_lambda

if TYPE_CHECKING:
    from runway.cfngin.context import Context  # pylint: disable=W
    from runway.cfngin.providers.base import BaseProvider  # pylint: disable=W

# The functions associated with Auth@Edge
FUNCTIONS = ["check_auth", "refresh_auth", "parse_auth", "sign_out", "http_headers"]


LOGGER = logging.getLogger(__name__)


def write(
    context,  # type: Context
    provider,  # type: BaseProvider
    **kwargs  # type: Optional[Dict[str, Any]]
):
    # type: (...) -> Dict[str, Any]
    """Writes/Uploads the configured lambdas for Auth@Edge.

    Lambda@Edge does not have the ability to allow Environment variables
    at the time of this writing. In order to configure our lambdas with
    dynamic variables we first will go through and update a "shared" template
    with all of the configuration elements and add that to a temporary
    folder along with each of the individual Lambda@Edge functions. This
    temporary folder is then used with the CFNgin awsLambda hook to build
    the functions.

    Args:
        context (cfngin.Context): The CFNgin context.
        provider (cfngin.Provider): The CFNgin provider.

    Keyword Args:
        client_id (str): The ID of the Cognito User Pool Client.
        cookie_settings (dict): The settings for our customized cookies.
        http_headers (dict): The additional headers added to our requests.
        oauth_scopes (List[str]): The validation scopes for our OAuth requests.
        redirect_path_auth_refresh (str): The URL path for authorization refresh
            redirect (Correlates to the refresh auth lambda).
        redirect_path_sign_in (str): The URL path to be redirected to after
            sign in (Correlates to the parse auth lambda).
        redirect_path_sign_out (str): The URL path to be redirected to after
            sign out (Correlates to the root to be asked to resigning).
        user_pool_id (str): The ID of the Cognito User Pool.

    """
    cognito_domain = context.hook_data["aae_domain_updater"].get("domain")
    config = {
        "client_id": kwargs["client_id"],
        "cognito_auth_domain": cognito_domain,
        "cookie_settings": kwargs["cookie_settings"],
        "http_headers": kwargs["http_headers"],
        "oauth_scopes": kwargs["oauth_scopes"],
        "redirect_path_auth_refresh": kwargs["redirect_path_refresh"],
        "redirect_path_sign_in": kwargs["redirect_path_sign_in"],
        "redirect_path_sign_out": kwargs["redirect_path_sign_out"],
        "user_pool_id": context.hook_data["aae_user_pool_id_retriever"]["id"],
    }

    # Shared file that contains the method called for configuration data
    path = os.path.join(os.path.dirname(__file__), "templates/shared.py")
    context_dict = {}

    with open(path) as file_:
        # Dynamically replace our configuration values
        # in the shared.py template file with actual
        # calculated values
        shared = re.sub(
            r"{.+?(})$", str(config), file_.read(), 1, flags=re.DOTALL | re.MULTILINE
        )

        filedir, temppath = mkstemp()

        # Save the file to a temp path
        with open(temppath, "w") as tmp:
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
                os.path.join(os.path.dirname(__file__), "templates/%s" % handler),
                dirpath,
            )

            # Save our dynamic configuration shared file to the
            # temporary folder
            with open(config) as shared:
                raw = shared.read()
                filename = "shared.py"
                with open("%s/%s" % (dirpath, filename), "wb") as newfile:
                    newfile.write(raw.encode())

            # Upload our temporary folder to our S3 bucket for
            # Lambda use
            lamb = aws_lambda.upload_lambda_functions(
                context,
                provider,
                bucket=kwargs["bucket"],
                functions={handler: {"path": dirpath}},
            )

            # Add the lambda code reference to our context_dict
            context_dict.update(lamb)

    return context_dict
