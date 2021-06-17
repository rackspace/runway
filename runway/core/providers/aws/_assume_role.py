"""Assume an AWS IAM role."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, ContextManager, Optional, Type, cast

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from types import TracebackType

    from mypy_boto3_sts.type_defs import AssumedRoleUserTypeDef, CredentialsTypeDef

    from ...._logging import RunwayLogger
    from ....context import RunwayContext


LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))

_KwargsTypeDef = TypedDict(
    "_KwargsTypeDef", DurationSeconds=int, RoleArn=str, RoleSessionName=str
)


class AssumeRole(ContextManager["AssumeRole"]):
    """Context manager for assuming an AWS role."""

    assumed_role_user: AssumedRoleUserTypeDef
    credentials: CredentialsTypeDef
    ctx: RunwayContext
    duration_seconds: int
    revert_on_exit: bool
    session_name: str = "runway"

    def __init__(
        self,
        context: RunwayContext,
        role_arn: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        revert_on_exit: bool = True,
        session_name: Optional[str] = None,
    ):
        """Instantiate class.

        Args:
            context: Runway context object.
            role_arn: ARN of role to be assumed.
            duration_seconds: Seconds that the assumed role's credentials will be
                valid for. (default: 3600)
            revert_on_exit: Whether credentials in the environment will be
                reverted upon exiting the context manager.
            session_name: Name to use for the assumed role session. (default: runway)

        """
        self.assumed_role_user = {"AssumedRoleId": "", "Arn": ""}
        self.credentials = {
            "AccessKeyId": "",
            "Expiration": datetime.now(),
            "SecretAccessKey": "",
            "SessionToken": "",
        }
        self.role_arn = role_arn
        self.ctx = context
        self.duration_seconds = duration_seconds or 3600
        self.revert_on_exit = revert_on_exit
        self.session_name = session_name or "runway"

    @property
    def _kwargs(self) -> _KwargsTypeDef:
        """Construct keyword arguments to pass to boto3 call."""
        return {
            "DurationSeconds": self.duration_seconds,
            "RoleArn": self.role_arn or "",
            "RoleSessionName": self.session_name,
        }

    def assume(self) -> None:
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
        if "Credentials" in response:
            self.assumed_role_user.update(response.get("AssumedRoleUser", {}))
            self.credentials.update(response["Credentials"])
            self.ctx.env.vars.update(
                {
                    "AWS_ACCESS_KEY_ID": response["Credentials"]["AccessKeyId"],
                    "AWS_SECRET_ACCESS_KEY": response["Credentials"]["SecretAccessKey"],
                    "AWS_SESSION_TOKEN": response["Credentials"]["SessionToken"],
                }
            )
            LOGGER.verbose("updated environment with assumed credentials")
        else:
            raise ValueError("assume_role did not return Credentials")

    def restore_existing_iam_env_vars(self) -> None:
        """Restore backed up IAM environment variables."""
        if not self.role_arn:
            LOGGER.debug("no role was assumed; not reverting credentials")
            return
        for k in self.ctx.current_aws_creds.keys():
            old = "OLD_" + k
            if self.ctx.env.vars.get(old):
                self.ctx.env.vars[k] = self.ctx.env.vars.pop(old)
                LOGGER.debug("reverted environment variables: %s", k)
            else:
                self.ctx.env.vars.pop(k, None)
                LOGGER.debug("removed environment variables: %s ", k)

    def save_existing_iam_env_vars(self) -> None:
        """Backup IAM environment variables for later restoration."""
        for k, v in self.ctx.current_aws_creds.items():
            new = "OLD_" + k
            LOGGER.debug('saving environment variable "%s" as "%s"', k, new)
            self.ctx.env.vars[new] = cast(str, v)

    def __enter__(self) -> AssumeRole:
        """Enter the context manager."""
        LOGGER.debug("entering aws.AssumeRole context manager...")
        self.assume()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit the context manager."""
        if self.revert_on_exit:
            self.restore_existing_iam_env_vars()
        LOGGER.debug("aws.AssumeRole context manager exited")
