"""Type definitions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

AnyPath: TypeAlias = "Path | str"
AnyPathConstrained = TypeVar("AnyPathConstrained", Path, str)


class Boto3CredentialsTypeDef(TypedDict, total=False):
    """Boto3 credentials."""

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str


class EnvVarsAwsCredentialsTypeDef(TypedDict, total=False):
    """AWS credentials from/for environment variables."""

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_SESSION_TOKEN: str
