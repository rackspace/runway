"""Base context classes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import boto3
import botocore.exceptions

from ..aws_sso_botocore.session import Session
from ..cfngin.ui import ui
from ..constants import BOTO3_CREDENTIAL_CACHE
from ..mixins import DelCachedPropMixin
from ..type_defs import Boto3CredentialsTypeDef
from .sys_info import SystemInfo

if TYPE_CHECKING:
    from .._logging import PrefixAdaptor, RunwayLogger
    from ..core.components import DeployEnvironment
    from ..type_defs import EnvVarsAwsCredentialsTypeDef

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class BaseContext(DelCachedPropMixin):
    """Base class for context objects."""

    env: DeployEnvironment
    """Object containing information about the environment being deployed to."""

    logger: PrefixAdaptor | RunwayLogger
    """Custom logger."""

    sys_info: SystemInfo
    """Information about the current system being used to run Runway."""

    work_dir: Path
    """Working directory used by Runway. Should always be a directory named ``.runway``."""

    def __init__(
        self,
        *,
        deploy_environment: DeployEnvironment,
        logger: PrefixAdaptor | RunwayLogger = LOGGER,
        work_dir: Path | None = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            deploy_environment: The current deploy environment.
            logger: Custom logger.
            work_dir: Working directory used by Runway.

        """
        self.env = deploy_environment
        self.logger = logger
        self.sys_info = SystemInfo()
        self.work_dir = work_dir or Path.cwd() / ".runway"

    @property
    def boto3_credentials(self) -> Boto3CredentialsTypeDef:
        """Return a dict of boto3 credentials."""
        return Boto3CredentialsTypeDef(
            **{
                key.lower(): value for key, value in self.current_aws_creds.items()
            }  # pyright: ignore[reportArgumentType]
        )

    @property
    def current_aws_creds(self) -> EnvVarsAwsCredentialsTypeDef:
        """AWS credentials from self.env_vars."""
        return self.env.aws_credentials

    @property
    def is_interactive(self) -> bool:
        """Whether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.

        """
        return not self.env.ci

    @property
    def is_noninteractive(self) -> bool:
        """Whether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.
        Inverse of ``is_interactive`` property.

        """
        return self.env.ci

    def get_session(
        self,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """Create a thread-safe boto3 session.

        If ``profile`` is provided, it will take priority.

        If no credential arguments are passed, will attempt to find them in
        environment variables.

        Args:
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS secret Access Key.
            aws_session_token: AWS session token.
            profile: The profile for the session.
            region: The region for the session.

        Returns:
            A thread-safe boto3 session.

        """
        if profile:
            self.logger.debug(
                'building session using profile "%s" in region "%s"',
                profile,
                region or "default",
            )
        else:  # use explicit values or grab values from env vars
            aws_access_key_id = aws_access_key_id or self.env.vars.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = aws_secret_access_key or self.env.vars.get(
                "AWS_SECRET_ACCESS_KEY"
            )
            aws_session_token = aws_session_token or self.env.vars.get("AWS_SESSION_TOKEN")
            if aws_access_key_id:
                self.logger.debug(
                    'building session with Access Key "%s" in region "%s"',
                    aws_access_key_id,
                    region or "default",
                )
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            botocore_session=Session(),
            region_name=region or self.env.aws_region,
            profile_name=profile,
        )
        cred_provider = session._session.get_component("credential_provider")  # type: ignore
        provider = cred_provider.get_provider("assume-role")  # type: ignore
        provider.cache = BOTO3_CREDENTIAL_CACHE
        provider._prompter = ui.getpass  # noqa: SLF001
        return session

    # TODO (kyle): remove after IaC tools support AWS SSO
    def _inject_profile_credentials(self) -> None:  # cov: ignore
        """Inject AWS credentials into self.env_vars if using an AWS profile.

        This is to enable support of AWS SSO profiles until all IaC tools that
        Runway wraps supports these types of profiles.

        """
        if self.current_aws_creds or not self.env.aws_profile:
            return

        try:
            creds = self.get_session(profile=self.env.aws_profile).get_credentials()
            if creds is not None:
                frozen_creds = creds.get_frozen_credentials()
                self.env.vars["AWS_ACCESS_KEY_ID"] = frozen_creds.access_key
                self.env.vars["AWS_SECRET_ACCESS_KEY"] = frozen_creds.secret_key
                if frozen_creds.token:
                    self.env.vars["AWS_SESSION_TOKEN"] = frozen_creds.token
            else:
                raise ValueError("Credentials could not be retrieved from the session.")
        except botocore.exceptions.BotoCoreError as boto_error:
            # Handle specific boto core exceptions
            self.logger.error("BotoCoreError occurred: %s", boto_error)
