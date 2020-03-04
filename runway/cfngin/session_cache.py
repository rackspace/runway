"""CFNgin session caching."""
import logging
import os
import warnings

import boto3

from .ui import ui

LOGGER = logging.getLogger(__name__)

DEFAULT_PROFILE = None
DEPRECATION_MSG = ('Use of "get_session" without providing credentials or a '
                   'profile has been deprecated and will raise an error after '
                   'the next major release. Please use the "get_session" '
                   'method of the context object instead.')
# A global credential cache that can be shared among boto3 sessions. This is
# inherently threadsafe thanks to the GIL:
# https://docs.python.org/3/glossary.html#term-global-interpreter-lock
CREDENTIAL_CACHE = {}


def get_session(region=None,
                profile=None,
                access_key=None,
                secret_key=None,
                session_token=None):
    """Create a thread-safe boto3 session.

    Args:
        region (Optional[str]): The region for the session.
        profile (Optional[str]): The profile for the session.
        access_key (Optional[str]): AWS Access Key ID.
        secret_key (Optional[str]): AWS secret Access Key.
        session_token (Optional[str]): AWS session token.

    Returns:
        :class:`boto3.session.Session`: A thread-safe boto3 session.

    """
    if profile:
        LOGGER.debug('Building session using profile "%s" in region "%s"',
                     profile, region or 'default')
    elif access_key:
        LOGGER.debug('Building session with Access Key "%s" in region "%s"',
                     access_key, region or 'default')
    elif os.environ.get('AWS_ACCESS_KEY_ID'):
        # TODO raise an error so we don't need to modify os.environ for cfngin
        warnings.warn(DEPRECATION_MSG, DeprecationWarning)
        # TODO uncomment log message after we update all internal use
        # LOGGER.warning(DEPRECATION_MSG)

    session = boto3.Session(aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            aws_session_token=session_token,
                            region_name=region,
                            profile_name=profile)
    cred_provider = session._session.get_component('credential_provider')
    provider = cred_provider.get_provider('assume-role')
    provider.cache = CREDENTIAL_CACHE
    provider._prompter = ui.getpass
    return session
