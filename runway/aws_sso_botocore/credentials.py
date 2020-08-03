"""Botocore with support for AWS SSO credential assets."""
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
# pylint: disable=too-few-public-methods
import datetime
import json
import logging
import os
from hashlib import sha1

from botocore import UNSIGNED
from botocore.config import Config
from botocore.credentials import (
    AssumeRoleProvider,
    BotoProvider,
    CachedCredentialFetcher,
    CanonicalNameCredentialSourcer,
    ContainerProvider,
    CredentialProvider,
    CredentialResolver,
    DeferredRefreshableCredentials,
    EnvProvider,
    InstanceMetadataFetcher,
    InstanceMetadataProvider,
    JSONFileCache,
    OriginalEC2Provider,
)
from botocore.credentials import (
    ProfileProviderBuilder as BotocoreProfileProviderBuilder,
)
from botocore.credentials import _get_client_creator, _serialize_if_needed
from botocore.exceptions import InvalidConfigError
from dateutil.tz import tzutc

from .exceptions import UnauthorizedSSOTokenError
from .util import SSOTokenLoader

LOGGER = logging.getLogger(__name__)


def create_credential_resolver(session, cache=None, region_name=None):
    """Create a default credential resolver.

    This creates a pre-configured credential resolver
    that includes the default lookup chain for
    credentials.

    """
    profile_name = session.get_config_variable('profile') or 'default'
    metadata_timeout = session.get_config_variable('metadata_service_timeout')
    num_attempts = session.get_config_variable('metadata_service_num_attempts')
    disable_env_vars = session.instance_variables().get('profile') is not None

    if cache is None:
        cache = {}

    env_provider = EnvProvider()
    container_provider = ContainerProvider()
    instance_metadata_provider = InstanceMetadataProvider(
        iam_role_fetcher=InstanceMetadataFetcher(
            timeout=metadata_timeout,
            num_attempts=num_attempts,
            user_agent=session.user_agent())
    )

    profile_provider_builder = ProfileProviderBuilder(
        session, cache=cache, region_name=region_name)
    assume_role_provider = AssumeRoleProvider(
        load_config=lambda: session.full_config,
        client_creator=_get_client_creator(session, region_name),
        cache=cache,
        profile_name=profile_name,
        credential_sourcer=CanonicalNameCredentialSourcer([
            env_provider, container_provider, instance_metadata_provider
        ]),
        profile_provider_builder=profile_provider_builder,
    )

    pre_profile = [
        env_provider,
        assume_role_provider,
    ]
    profile_providers = profile_provider_builder.providers(
        profile_name=profile_name,
        disable_env_vars=disable_env_vars,
    )
    post_profile = [
        OriginalEC2Provider(),
        BotoProvider(),
        container_provider,
        instance_metadata_provider,
    ]
    providers = pre_profile + profile_providers + post_profile

    if disable_env_vars:
        # An explicitly provided profile will negate an EnvProvider.
        # We will defer to providers that understand the "profile"
        # concept to retrieve credentials.
        # The one edge case if is all three values are provided via
        # env vars:
        # export AWS_ACCESS_KEY_ID=foo
        # export AWS_SECRET_ACCESS_KEY=bar
        # export AWS_PROFILE=baz
        # Then, just like our client() calls, the explicit credentials
        # will take precedence.
        #
        # This precedence is enforced by leaving the EnvProvider in the chain.
        # This means that the only way a "profile" would win is if the
        # EnvProvider does not return credentials, which is what we want
        # in this scenario.
        providers.remove(env_provider)
        LOGGER.debug('Skipping environment variable credential check'
                     ' because profile name was explicitly set.')

    return CredentialResolver(providers=providers)


class ProfileProviderBuilder(BotocoreProfileProviderBuilder):
    """Extends the botocore profile provider builder to support AWS SSO."""

    def __init__(self, session, cache=None, region_name=None,
                 sso_token_cache=None):
        """Instantiate class."""
        super(ProfileProviderBuilder, self).__init__(session, cache, region_name)
        self._sso_token_cache = sso_token_cache

    def providers(self, profile_name, disable_env_vars=False):
        """Return list of providers."""
        return [
            self._create_web_identity_provider(
                profile_name, disable_env_vars,
            ),
            self._create_sso_provider(profile_name),
            self._create_shared_credential_provider(profile_name),
            self._create_process_provider(profile_name),
            self._create_config_provider(profile_name),
        ]

    def _create_sso_provider(self, profile_name):
        """AWS SSO credential provider."""
        return SSOProvider(
            load_config=lambda: self._session.full_config,
            client_creator=self._session.create_client,
            profile_name=profile_name,
            cache=self._cache,
            token_cache=self._sso_token_cache,
        )


class SSOCredentialFetcher(CachedCredentialFetcher):
    """AWS SSO credential fetcher."""

    def __init__(self, start_url, sso_region, role_name, account_id,
                 client_creator, token_loader=None, cache=None,
                 expiry_window_seconds=None):
        """Instantiate class."""
        self._client_creator = client_creator
        self._sso_region = sso_region
        self._role_name = role_name
        self._account_id = account_id
        self._start_url = start_url
        self._token_loader = token_loader

        super(SSOCredentialFetcher, self).__init__(
            cache, expiry_window_seconds
        )

    def _create_cache_key(self):
        """Create a predictable cache key for the current configuration.

        The cache key is intended to be compatible with file names.

        """
        args = {
            'startUrl': self._start_url,
            'roleName': self._role_name,
            'accountId': self._account_id,
        }
        # NOTE: It would be good to hoist this cache key construction logic
        # into the CachedCredentialFetcher class as we should be consistent.
        # Unfortunately, the current assume role fetchers that sub class don't
        # pass separators resulting in non-minified JSON. In the long term,
        # all fetchers should use the below caching scheme.
        args = json.dumps(args, sort_keys=True, separators=(',', ':'))
        argument_hash = sha1(args.encode('utf-8')).hexdigest()
        return self._make_file_safe(argument_hash)

    def _parse_timestamp(self, timestamp_ms):  # pylint: disable=no-self-use
        """Parse timestamp."""
        # fromtimestamp expects seconds so: milliseconds / 1000 = seconds
        timestamp_seconds = timestamp_ms / 1000.0
        timestamp = datetime.datetime.fromtimestamp(timestamp_seconds, tzutc())
        return _serialize_if_needed(timestamp)

    def _get_credentials(self):
        """Get credentials by calling SSO get role credentials."""
        config = Config(
            signature_version=UNSIGNED,
            region_name=self._sso_region,
        )
        client = self._client_creator('sso', config=config)

        kwargs = {
            'roleName': self._role_name,
            'accountId': self._account_id,
            'accessToken': self._token_loader(self._start_url),
        }
        try:
            response = client.get_role_credentials(**kwargs)
        except client.exceptions.UnauthorizedException:
            raise UnauthorizedSSOTokenError()
        credentials = response['roleCredentials']

        credentials = {
            'ProviderType': 'sso',
            'Credentials': {
                'AccessKeyId': credentials['accessKeyId'],
                'SecretAccessKey': credentials['secretAccessKey'],
                'SessionToken': credentials['sessionToken'],
                'Expiration': self._parse_timestamp(credentials['expiration']),
            }
        }
        return credentials


class SSOProvider(CredentialProvider):
    """AWS SSO credential provider."""

    METHOD = 'sso'

    _SSO_TOKEN_CACHE_DIR = os.path.expanduser(
        os.path.join('~', '.aws', 'sso', 'cache')
    )
    _SSO_CONFIG_VARS = [
        'sso_start_url',
        'sso_region',
        'sso_role_name',
        'sso_account_id',
    ]

    # pylint: disable=super-init-not-called
    def __init__(self, load_config, client_creator, profile_name,
                 cache=None, token_cache=None):
        """Instantiate class."""
        if token_cache is None:
            token_cache = JSONFileCache(self._SSO_TOKEN_CACHE_DIR)
        self._token_cache = token_cache
        if cache is None:
            cache = {}
        self.cache = cache
        self._load_config = load_config
        self._client_creator = client_creator
        self._profile_name = profile_name

    def _load_sso_config(self):
        """Load sso config."""
        loaded_config = self._load_config()
        profiles = loaded_config.get('profiles', {})
        profile_name = self._profile_name
        profile_config = profiles.get(self._profile_name, {})

        if all(c not in profile_config for c in self._SSO_CONFIG_VARS):
            return None

        config = {}
        missing_config_vars = []
        for config_var in self._SSO_CONFIG_VARS:
            if config_var in profile_config:
                config[config_var] = profile_config[config_var]
            else:
                missing_config_vars.append(config_var)

        if missing_config_vars:
            missing = ', '.join(missing_config_vars)
            raise InvalidConfigError(
                error_msg=(
                    'The profile "%s" is configured to use SSO but is missing '
                    'required configuration: %s' % (profile_name, missing)
                )
            )

        return config

    def load(self):
        """Load AWS SSO credentials."""
        sso_config = self._load_sso_config()
        if not sso_config:
            return None

        sso_fetcher = SSOCredentialFetcher(
            sso_config['sso_start_url'],
            sso_config['sso_region'],
            sso_config['sso_role_name'],
            sso_config['sso_account_id'],
            self._client_creator,
            token_loader=SSOTokenLoader(cache=self._token_cache),
            cache=self.cache,
        )

        return DeferredRefreshableCredentials(
            method=self.METHOD,
            refresh_using=sso_fetcher.fetch_credentials,
        )
