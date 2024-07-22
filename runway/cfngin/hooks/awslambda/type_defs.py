"""Type definitions."""

from __future__ import annotations

from typing_extensions import TypedDict


class AwsLambdaHookDeployResponseTypedDict(TypedDict):
    """Dict output of :class:`runway.cfngin.hooks.awslambda.models.response.AwsLambdaHookDeployResponse` using aliases."""  # noqa: E501

    CodeSha256: str
    Runtime: str
    S3Bucket: str
    S3Key: str
    S3ObjectVersion: str | None
