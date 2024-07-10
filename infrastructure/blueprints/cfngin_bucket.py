"""Blueprint for a CFNgin Bucket."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

from troposphere import And, Equals, If, Not, NoValue, s3

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString
from runway.compat import cached_property

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class CfnginBucket(Blueprint):
    """Blueprint for a CFNgin Bucket."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "BucketName": {
            "type": CFNString,
            "description": "Name for the S3 bucket",
            "default": "",
        },
        "DeletionPolicy": {
            "type": str,
            "allowed_values": ["Delete", "Retain"],
            "description": "CloudFormation deletion policy",
            "default": "Delete",
        },
    }

    @cached_property
    def condition_bucket_name_provided(self) -> str:
        """Condition BucketNameProvided."""
        return self.template.add_condition(
            "BucketNameProvided",
            And(
                Not(Equals(self.variables["BucketName"].ref, "undefined")),
                Not(Equals(self.variables["BucketName"].ref, "")),
            ),
        )

    @cached_property
    def bucket_name(self) -> If:
        """Name of the S3 bucket."""
        return If(
            self.condition_bucket_name_provided,
            self.variables["BucketName"].ref,
            NoValue,
        )

    def create_template(self) -> None:
        """Create a template from the Blueprint."""
        self.template.set_description("CFNgin Bucket")
        self.template.set_version("2010-09-09")

        bucket = s3.Bucket(
            "Bucket",
            template=self.template,
            AccessControl=s3.Private,
            BucketName=self.bucket_name,
            DeletionPolicy=self.variables["DeletionPolicy"],
            LifecycleConfiguration=s3.LifecycleConfiguration(
                Rules=[s3.LifecycleRule(NoncurrentVersionExpirationInDays=30, Status="Enabled")]
            ),
            VersioningConfiguration=s3.VersioningConfiguration(Status="Enabled"),
        )
        self.add_output(f"{bucket.title}Name", bucket.ref())
        self.add_output(f"{bucket.title}Arn", bucket.get_att("Arn"))
