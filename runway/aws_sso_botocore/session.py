"""Botocore with support for AWS SSO session assets."""
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
from botocore.session import Session as BotocoreSession

from .credentials import create_credential_resolver


class Session(BotocoreSession):
    """Extends the botocore session to support AWS SSO."""

    def _create_credential_resolver(self):
        """Replace the parent method with one that includes AWS SSO support."""
        return create_credential_resolver(
            self, region_name=self._last_client_region_used
        )
