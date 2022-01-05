"""Type definitions."""
from __future__ import annotations

from typing import Optional

from typing_extensions import TypedDict


class AwsLambdaHookDeployResponseTypedDict(TypedDict):
    """Dict output of :class:`runway.cfngin.hooks.awslambda.models.response.AwsLambdaHookDeployResponse` using aliases."""  # noqa

    CodeSha256: str
    Runtime: str
    S3Bucket: str
    S3Key: str
    S3ObjectVersion: Optional[str]
