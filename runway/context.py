"""Runway context module."""
from __future__ import annotations

import logging
import sys
from distutils.util import strtobool
from typing import TYPE_CHECKING, Dict, Optional, cast

from .cfngin.session_cache import get_session
from .core.components import DeployEnvironment
from .type_defs import Boto3CredentialsTypeDef
from .util import cached_property

if TYPE_CHECKING:
    import boto3

    from ._logging import RunwayLogger
    from .type_defs import EnvVarsAwsCredentials

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class Context:
    """Runway execution context."""

    command: Optional[str]
    debug: bool
    env: DeployEnvironment

    def __init__(
        self,
        *,
        command: Optional[str] = None,
        deploy_environment: Optional[DeployEnvironment] = None
    ) -> None:
        """Instantiate class.

        Args:
            command: Runway command/action being run.
            deploy_environment: Current deploy environment.

        """
        self.command = command
        self.env = deploy_environment or DeployEnvironment()
        self.debug = self.env.debug
        # TODO remove after IaC tools support AWS SSO
        self.__inject_profile_credentials()

    @property
    def boto3_credentials(self) -> Boto3CredentialsTypeDef:
        """Return a dict of boto3 credentials."""
        return Boto3CredentialsTypeDef(
            **{key.lower(): value for key, value in self.current_aws_creds.items()}
        )

    @property
    def current_aws_creds(self) -> EnvVarsAwsCredentials:
        """AWS credentials from self.env_vars."""
        return self.env.aws_credentials

    @cached_property
    def env_name(self) -> str:
        """Get name from deploy environment [DEPRECATED]."""
        return self.env.name

    @property
    def env_region(self) -> str:
        """Get or set the current AWS region [DEPRECATED]."""
        return self.env.aws_region

    @env_region.setter
    def env_region(self, region: str) -> None:
        """Set the AWS region [DEPRECATED]."""
        self.env.aws_region = region

    @property
    def env_root(self) -> str:
        """Get environment root directory [DEPRECATED]."""
        return str(self.env.root_dir)

    @property
    def env_vars(self) -> Dict[str, str]:
        """Get environment variables [DEPRECATED]."""
        return self.env.vars

    @cached_property
    def no_color(self) -> bool:
        """Whether to explicitly disable color output.

        Primarily applies to IaC being wrapped by Runway.

        Returns:
            bool

        """
        colorize = self.env.vars.get("RUNWAY_COLORIZE")  # explicitly enable/disable
        try:
            if isinstance(colorize, bool):  # catch False
                return not colorize
            if colorize and isinstance(colorize, str):
                return not strtobool(colorize)
        except ValueError:
            pass  # likely invalid RUNWAY_COLORIZE value
        return not sys.stdout.isatty()

    @property
    def is_interactive(self) -> bool:
        """Whether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.

        Returns:
            bool

        """
        return not self.env.ci

    @property
    def is_noninteractive(self) -> bool:
        """Whether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.
        Inverse of ``is_interactive`` property.

        Returns:
            bool

        """
        return self.env.ci

    @property
    def use_concurrent(self) -> bool:
        """Whether to use concurrent.futures or not.

        Noninteractive is required for concurrent execution to prevent weird
        user-input behavior.

        Python 3 is required because backported futures has issues with
        ProcessPoolExecutor.

        """
        if self.is_noninteractive:
            return True
        LOGGER.warning("Parallel execution disabled; not running in CI mode")
        return False

    def copy(self) -> Context:
        """Copy the contents of this object into a new instance.

        Returns:
            Context: New instance with the same contents.

        """
        LOGGER.debug("creating a copy of Runway context...")
        return self.__class__(command=self.command, deploy_environment=self.env.copy())

    def echo_detected_environment(self) -> None:
        """Print a helper note about how the environment was determined."""
        self.env.log_name()

    def get_session(
        self, profile: Optional[str] = None, region: Optional[str] = None
    ) -> boto3.Session:
        """Create a thread-safe boto3 session.

        Args:
            profile: The profile for the session.
            region: The region for the session.

        Returns:
            A thread-safe boto3 session.

        """
        kwargs = {}
        # save to var so its not calculated multiple times
        creds = self.boto3_credentials
        if profile:
            LOGGER.verbose('creating AWS session using profile "%s"...', profile)
            kwargs["profile"] = profile
        elif creds:
            LOGGER.verbose(
                "creating AWS session using credentials from the environment..."
            )
            kwargs.update(
                {
                    "access_key": creds.get("aws_access_key_id"),
                    "secret_key": creds.get("aws_secret_access_key"),
                    "session_token": creds.get("aws_session_token"),
                }
            )
        return get_session(region=region or self.env.aws_region, **kwargs)

    # TODO remove after IaC tools support AWS SSO
    def __inject_profile_credentials(self) -> None:  # cov: ignore
        """Inject AWS credentials into self.env_vars if using an AWS profile.

        This is to enable support of AWS SSO profiles until all IaC tools that
        Runway wraps supports these types of profiles.

        """
        if self.current_aws_creds or not self.env.aws_profile:
            return

        creds = (
            self.get_session(profile=self.env.aws_profile)
            .get_credentials()
            .get_frozen_credentials()
        )

        self.env.vars["AWS_ACCESS_KEY_ID"] = creds.access_key
        self.env.vars["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
        if creds.token:
            self.env.vars["AWS_SESSION_TOKEN"] = creds.token
