"""Response data models."""
from typing import List, Optional

from pydantic import Extra

from runway.utils import BaseModel


class AwsLambdaHookDeployResponse(BaseModel):
    """Data model for AwsLambdaHook deploy response.

    When returned by the hook as ``hook_data``, this model is dumped to a
    standard :class:`~typing.Dict` using the field's aliases as the ``key`` in
    place of the attribute names.
    This is done so that the ``key`` is a direct match to a CloudFormation
    Property where the value should be used.

    """

    bucket_name: str
    """Name of the S3 Bucket where the deployment package is located. (alias ``S3Bucket``)"""

    code_sha256: str
    """SHA256 of the deployment package.
    This can be used by CloudFormation as the value of ``AWS::Lambda::Version.CodeSha256``.
    (alias ``CodeSha256``)

    """

    compatible_architectures: Optional[List[str]] = None
    """A list of compatible instruction set architectures.
    (https://docs.aws.amazon.com/lambda/latest/dg/foundation-arch.html)
    (alias ``CompatibleArchitectures``)

    """

    compatible_runtimes: Optional[List[str]] = None
    """A list of compatible function runtimes.
    Used for filtering with ``ListLayers`` and ``ListLayerVersions``.
    (alias ``CompatibleRuntimes``)

    """

    license: Optional[str] = None
    """The layer's software license (alias ``License``). Can be any of the following:

    - A SPDX license identifier (e.g. ``MIT``).
    - The URL of a license hosted on the internet (e.g.
      ``https://opensource.org/licenses/MIT``).
    - The full text of the license.

    """

    object_key: str
    """Key (file path) of the deployment package S3 Object. (alias ``S3Key``)"""

    object_version_id: Optional[str] = None
    """The version ID of the deployment package S3 Object.
    This will only have a value if the S3 Bucket has versioning enabled.
    (alias ``S3ObjectVersion``)

    """

    runtime: str
    """Runtime of the Lambda Function. (alias ``Runtime``)"""

    class Config:
        """Model configuration."""

        allow_population_by_field_name = True
        extra = Extra.forbid
        fields = {
            "bucket_name": {"alias": "S3Bucket"},
            "code_sha256": {"alias": "CodeSha256"},
            "compatible_architectures": {"alias": "CompatibleArchitectures"},
            "compatible_runtimes": {"alias": "CompatibleRuntimes"},
            "license": {"alias": "License"},
            "object_key": {"alias": "S3Key"},
            "object_version_id": {"alias": "S3ObjectVersion"},
            "runtime": {"alias": "Runtime"},
        }
