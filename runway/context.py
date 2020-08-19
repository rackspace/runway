"""Runway context module."""
import logging
import sys
from distutils.util import strtobool  # pylint: disable=E

from six import string_types

from .cfngin.session_cache import get_session
from .core.components import DeployEnvironment
from .util import cached_property

LOGGER = logging.getLogger(__name__)


class Context(object):
    """Runway execution context."""

    # TODO implement propper keyword-only args when dropping python 2
    # def __init__(self,
    #              *: Any,
    #              command: Optional[str] = None,
    #              deploy_environment: Optional[DeployEnvironment] = None
    #              ) -> None:
    def __init__(self, _=None, **kwargs):
        """Instantiate class.

        Keywork Arguments:
            command (Optional[str]): Runway command/action being run.
            deploy_environment (Optional[DeployEnvironment]): Current
                deploy environment.

        """
        self.command = kwargs.pop("command", None)
        self.env = kwargs.pop("deploy_environment", DeployEnvironment())
        self.debug = self.env.debug
        # TODO remove after IaC tools support AWS SSO
        self.__inject_profile_credentials()

    @property
    def boto3_credentials(self):
        """Return a dict of boto3 credentials."""
        return {key.lower(): value for key, value in self.current_aws_creds.items()}

    @property
    def current_aws_creds(self):
        """AWS credentials from self.env_vars.

        Returns:
            Dict[str, str]

        """
        return self.env.aws_credentials

    @cached_property
    def env_name(self):
        """Get name from deploy environment [DEPRECATED]."""
        return self.env.name

    @property
    def env_region(self):
        # type: () -> str
        """Get or set the current AWS region [DEPRECATED]."""
        return self.env.aws_region

    @env_region.setter
    def env_region(self, region):
        # type: (str) -> None
        """Set the AWS region [DEPRECATED]."""
        self.env.aws_region = region

    @property
    def env_root(self):
        """Get environment root directory [DEPRECATED]."""
        return str(self.env.root_dir)

    @property
    def env_vars(self):
        """Get environment variables [DEPRECATED]."""
        return self.env.vars

    @cached_property
    def no_color(self):
        # type: () -> bool
        """Wether to explicitly disable color output.

        Primarily applies to IaC being wrapped by Runway.

        Returns:
            bool

        """
        colorize = self.env.vars.get("RUNWAY_COLORIZE")  # explicitly enable/disable
        try:
            if isinstance(colorize, bool):  # catch False
                return not colorize
            if colorize and isinstance(colorize, string_types):
                return not strtobool(colorize)
        except ValueError:
            pass  # likely invalid RUNWAY_COLORIZE value
        return not sys.stdout.isatty()

    @property
    def is_interactive(self):
        # type: () -> bool
        """Wether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.

        Returns:
            bool

        """
        return not self.env.ci

    @property
    def is_noninteractive(self):
        # type: () -> bool
        """Wether the user should be prompted or not.

        Determined by the existed of ``CI`` in the environment.
        Inverse of ``is_interactive`` property.

        Returns:
            bool

        """
        return self.env.ci

    @property
    def is_python3(self):
        # type: () -> bool
        """Wether running in Python 3 or not.

        Used for Python compatability decisions.

        Returns:
            bool

        """
        return sys.version_info.major > 2

    @property
    def use_concurrent(self):
        # type: () -> bool
        """Wether to use concurrent.futures or not.

        Noninteractive is required for concurrent execution to prevent weird
        user-input behavior.

        Python 3 is required because backported futures has issues with
        ProcessPoolExecutor.

        Returns:
            bool

        """
        if self.is_noninteractive:
            if self.is_python3:
                return True
            LOGGER.warning("Parallel execution disabled; Python 3+ is required")
        LOGGER.warning("Parallel execution disabled; not running in CI mode")
        return False

    def copy(self):
        # type: () -> Context
        """Copy the contents of this object into a new instance.

        Returns:
            Context: New instance with the same contents.

        """
        LOGGER.debug("creating a copy of Runway context...")
        return self.__class__(command=self.command, deploy_environment=self.env.copy())

    def echo_detected_environment(self):
        # type: () -> None
        """Print a helper note about how the environment was determined."""
        self.env.log_name()

    def get_session(self, profile=None, region=None):
        """Create a thread-safe boto3 session.

        Args:
            profile (Optional[str]): The profile for the session.
            region (Optional[str]): The region for the session.

        Returns:
            :class:`boto3.session.Session`: A thread-safe boto3 session.

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
    def __inject_profile_credentials(self):  # cov: ignore
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
