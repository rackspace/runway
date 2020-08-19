"""Assume an AWS IAM role."""
import logging
import sys

if sys.version_info >= (3, 6):  # cov: ignore
    from contextlib import AbstractContextManager  # pylint: disable=E
else:  # cov: ignore
    AbstractContextManager = object

LOGGER = logging.getLogger(__name__.replace("._", "."))


class AssumeRole(AbstractContextManager):
    """Context manager for assuming an AWS role."""

    def __init__(
        self,
        context,
        role_arn=None,
        duration_seconds=None,
        revert_on_exit=True,
        session_name=None,
    ):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            role_arn (Optional[str]): ARN of role to be assumed.
            duration_seconds (Optional[int]): Seconds that the assumed role's
                credentials will be valid for. (default: 3600)
            revert_on_exit (bool): Whether credentials in the environment will
                be reverted upon exiting the context manager.
            session_name (Optional[bool]): Name to use for the assumed role
                session. (default: runway)

        """
        self.role_arn = role_arn
        self.assumed_role_user = {}
        self.credentials = {}
        self.ctx = context
        self.duration_seconds = duration_seconds or 3600
        self.revert_on_exit = revert_on_exit
        self.session_name = session_name or "runway"

    @property
    def _kwargs(self):
        """Construct keyword arguments to pass to boto3 call.

        Returns:
            Dict[str, Union[int, str]]: Keyword arguments for boto3 call.

        """
        return {
            "RoleArn": self.role_arn,
            "RoleSessionName": self.session_name,
            "DurationSeconds": self.duration_seconds,
        }

    def assume(self):
        """Perform role assumption."""
        if not self.role_arn:
            LOGGER.debug("no role to assume")
            return
        if self.revert_on_exit:
            self.save_existing_iam_env_vars()
        sts_client = self.ctx.get_session().client("sts")
        LOGGER.info("assuming role %s...", self.role_arn)
        response = sts_client.assume_role(**self._kwargs)
        LOGGER.debug("sts.assume_role respsone: %s", response)
        self.assumed_role_user.update(response["AssumedRoleUser"])
        self.credentials.update(response["Credentials"])
        self.ctx.env.vars.update(
            {
                "AWS_ACCESS_KEY_ID": response["Credentials"]["AccessKeyId"],
                "AWS_SECRET_ACCESS_KEY": response["Credentials"]["SecretAccessKey"],
                "AWS_SESSION_TOKEN": response["Credentials"]["SessionToken"],
            }
        )
        LOGGER.verbose("updated environment with assumed credentials")

    def restore_existing_iam_env_vars(self):
        """Restore backed up IAM environment variables."""
        if not self.role_arn:
            LOGGER.debug("no role was assumed; not reverting credentials")
            return
        for k in self.ctx.current_aws_creds.keys():
            old = "OLD_" + k
            if self.ctx.env_vars.get(old):
                self.ctx.env_vars[k] = self.ctx.env_vars.pop(old)
                LOGGER.debug("reverted environment variables: %s", k)
            else:
                self.ctx.env_vars.pop(k, None)
                LOGGER.debug("removed environment variables: %s ", k)

    def save_existing_iam_env_vars(self):
        """Backup IAM environment variables for later restoration."""
        for k, v in self.ctx.current_aws_creds.items():
            new = "OLD_" + k
            LOGGER.debug('saving environment variable "%s" as "%s"', k, new)
            self.ctx.env_vars[new] = v

    def __enter__(self):
        """Enter the context manager.

        Returns:
            AssumeRole

        """
        LOGGER.debug("entering aws.AssumeRole context manager...")
        self.assume()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        if self.revert_on_exit:
            self.restore_existing_iam_env_vars()
        LOGGER.debug("aws.AssumeRole context manager exited")
