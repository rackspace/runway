"""CFNgin session caching."""
import logging

import boto3

from .ui import ui

LOGGER = logging.getLogger(__name__)


# A global credential cache that can be shared among boto3 sessions. This is
# inherently threadsafe thanks to the GIL:
# https://docs.python.org/3/glossary.html#term-global-interpreter-lock
CREDENTIAL_CACHE = {}

DEFAULT_PROFILE = None


def get_session(region, profile=None):
    """Create a boto3 session or get a matching session from the cache.

    Args:
        region (str): The region for the session.
        profile (str): The profile for the session.

    Returns:
        :class:`boto3.session.Session`: A boto3 session with
        credential caching.

    """
    if profile is None:
        LOGGER.debug("No AWS profile explicitly provided. "
                     "Falling back to default.")
        profile = DEFAULT_PROFILE

    LOGGER.debug("Building session using profile \"%s\" in region \"%s\"",
                 profile, region)

    session = boto3.Session(region_name=region, profile_name=profile)
    cred_provider = session._session.get_component('credential_provider')
    provider = cred_provider.get_provider('assume-role')
    provider.cache = CREDENTIAL_CACHE
    provider._prompter = ui.getpass
    return session
