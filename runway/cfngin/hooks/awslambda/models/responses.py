"""Response data models."""

from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field

from runway.utils import BaseModel


class AwsLambdaHookDeployResponse(BaseModel):
    """Data model for AwsLambdaHook deploy response.

    When returned by the hook as ``hook_data``, this model is dumped to a
    standard :class:`~typing.Dict` using the field's aliases as the ``key`` in
    place of the attribute names.
    This is done so that the ``key`` is a direct match to a CloudFormation
    Property where the value should be used.

    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bucket_name: Annotated[str, Field(alias="S3Bucket")]
    """Name of the S3 Bucket where the deployment package is located. (alias ``S3Bucket``)"""

    code_sha256: Annotated[str, Field(alias="CodeSha256")]
    """SHA256 of the deployment package.
    This can be used by CloudFormation as the value of ``AWS::Lambda::Version.CodeSha256``.
    (alias ``CodeSha256``)

    """

    compatible_architectures: Annotated[
        list[str] | None, Field(alias="CompatibleArchitectures")
    ] = None
    """A list of compatible instruction set architectures.
    (https://docs.aws.amazon.com/lambda/latest/dg/foundation-arch.html)
    (alias ``CompatibleArchitectures``)

    """

    compatible_runtimes: Annotated[list[str] | None, Field(alias="CompatibleRuntimes")] = None
    """A list of compatible function runtimes.
    Used for filtering with ``ListLayers`` and ``ListLayerVersions``.
    (alias ``CompatibleRuntimes``)

    """

    license: Annotated[str | None, Field(alias="License")] = None
    """The layer's software license (alias ``License``). Can be any of the following:

    - A SPDX license identifier (e.g. ``MIT``).
    - The URL of a license hosted on the internet (e.g.
      ``https://opensource.org/licenses/MIT``).
    - The full text of the license.

    """

    object_key: Annotated[str, Field(alias="S3Key")]
    """Key (file path) of the deployment package S3 Object. (alias ``S3Key``)"""

    object_version_id: Annotated[str | None, Field(alias="S3ObjectVersion")] = None
    """The version ID of the deployment package S3 Object.
    This will only have a value if the S3 Bucket has versioning enabled.
    (alias ``S3ObjectVersion``)

    """

    runtime: Annotated[str, Field(alias="Runtime")]
    """Runtime of the Lambda Function. (alias ``Runtime``)"""
