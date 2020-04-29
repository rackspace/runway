"""Botocore with support for AWS SSO utilities."""
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
import hashlib
import logging

from .exceptions import SSOTokenLoadError

LOGGER = logging.getLogger(__name__)


class SSOTokenLoader(object):  # pylint: disable=too-few-public-methods
    """AWS SSO token loader."""

    def __init__(self, cache=None):
        """Instantiate class."""
        if cache is None:
            cache = {}
        self._cache = cache

    @staticmethod
    def _generate_cache_key(start_url):
        """Generate cache key."""
        return hashlib.sha1(start_url.encode('utf-8')).hexdigest()

    def __call__(self, start_url):
        """Call instance of class directly."""
        cache_key = self._generate_cache_key(start_url)
        try:
            token = self._cache[cache_key]
            return token['accessToken']
        except KeyError:
            LOGGER.debug('Failed to load SSO token:', exc_info=True)
            error_msg = (
                'The SSO access token has either expired or is otherwise '
                'invalid.'
            )
            raise SSOTokenLoadError(error_msg=error_msg)
