"""CFNgin session caching."""
import logging
import os
from typing import Optional

import boto3

from runway.aws_sso_botocore.session import Session

from .ui import ui

LOGGER = logging.getLogger(__name__)

DEFAULT_PROFILE = None
DEPRECATION_MSG = (
    '"session_cache.get_session" has been deprecated; '
    'use the "get_session" method of the context object instead'
)
# A global credential cache that can be shared among boto3 sessions. This is
# inherently threadsafe thanks to the GIL:
# https://docs.python.org/3/glossary.html#term-global-interpreter-lock
CREDENTIAL_CACHE = {}


def get_session(
    region: Optional[str] = None,
    profile: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    session_token=None,
) -> boto3.Session:
    """Create a thread-safe boto3 session.

    Args:
        region: The region for the session.
        profile: The profile for the session.
        access_key: AWS Access Key ID.
        secret_key: AWS secret Access Key.
        session_token: AWS session token.

    Returns:
        A thread-safe boto3 session.

    """
    if profile:
        LOGGER.debug(
            'building session using profile "%s" in region "%s"',
            profile,
            region or "default",
        )
    elif access_key:
        LOGGER.debug(
            'building session with Access Key "%s" in region "%s"',
            access_key,
            region or "default",
        )
    elif os.environ.get("AWS_ACCESS_KEY_ID"):
        LOGGER.warning(DEPRECATION_MSG)

    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        botocore_session=Session(),  # type: ignore
        region_name=region,
        profile_name=profile,
    )
    cred_provider = session._session.get_component("credential_provider")  # type: ignore
    provider = cred_provider.get_provider("assume-role")
    provider.cache = CREDENTIAL_CACHE
    provider._prompter = ui.getpass
    return session
