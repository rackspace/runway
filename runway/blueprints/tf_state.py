#!/usr/bin/env python
"""Module with Terraform state resources."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

import awacs.dynamodb
import awacs.s3
from awacs.aws import Allow, PolicyDocument, Statement
from troposphere import Equals, If, Join, NoValue, Or, Output, dynamodb, iam, s3

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class TfState(Blueprint):
    """CFNgin blueprint for creating Terraform state resources."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "BucketDeletionPolicy": {
            "type": str,
            "allowed_values": ["Delete", "Retain"],
            "description": "CloudFormation deletion policy",
            "default": "Retain",
        },
        "BucketName": {
            "type": CFNString,
            "description": "(optional) Name for the S3 bucket",
            "default": "",
        },
        "TableName": {
            "type": CFNString,
            "description": "(optional) Name for the DynamoDB table",
            "default": "",
        },
    }

    def create_template(self) -> None:
        """Create template (main function called by CFNgin)."""
        self.template.set_version("2010-09-09")
        self.template.set_description("Terraform State Resources")

        # Conditions
        for i in ["BucketName", "TableName"]:
            self.template.add_condition(
                f"{i}Omitted",
                Or(
                    Equals(self.variables[i].ref, ""),
                    Equals(self.variables[i].ref, "undefined"),
                ),
            )

        # Resources
        terraformlocktable = self.template.add_resource(
            dynamodb.Table(
                "TerraformStateTable",
                AttributeDefinitions=[
                    dynamodb.AttributeDefinition(
                        AttributeName="LockID", AttributeType="S"
                    )
                ],
                KeySchema=[dynamodb.KeySchema(AttributeName="LockID", KeyType="HASH")],
                ProvisionedThroughput=dynamodb.ProvisionedThroughput(
                    ReadCapacityUnits=2, WriteCapacityUnits=2
                ),
                TableName=If(
                    "TableNameOmitted", NoValue, self.variables["TableName"].ref
                ),
            )
        )
        self.template.add_output(
            Output(
                f"{terraformlocktable.title}Name",
                Description="Name of DynamoDB table for Terraform state",
                Value=terraformlocktable.ref(),
            )
        )

        terraformstatebucket = self.template.add_resource(
            s3.Bucket(
                "TerraformStateBucket",
                DeletionPolicy=self.variables["BucketDeletionPolicy"],
                AccessControl=s3.Private,
                BucketName=If(
                    "BucketNameOmitted", NoValue, self.variables["BucketName"].ref
                ),
                LifecycleConfiguration=s3.LifecycleConfiguration(
                    Rules=[
                        s3.LifecycleRule(
                            NoncurrentVersionExpirationInDays=90, Status="Enabled"
                        )
                    ]
                ),
                VersioningConfiguration=s3.VersioningConfiguration(Status="Enabled"),
            )
        )
        self.template.add_output(
            Output(
                f"{terraformstatebucket.title}Name",
                Description="Name of bucket storing Terraform state",
                Value=terraformstatebucket.ref(),
            )
        )
        self.template.add_output(
            Output(
                f"{terraformstatebucket.title}Arn",
                Description="Arn of bucket storing Terraform state",
                Value=terraformstatebucket.get_att("Arn"),
            )
        )

        managementpolicy = self.template.add_resource(
            iam.ManagedPolicy(
                "ManagementPolicy",
                Description="Managed policy for Terraform state management.",
                Path="/",
                PolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=[
                        # https://www.terraform.io/docs/backends/types/s3.html#s3-bucket-permissions
                        Statement(
                            Action=[awacs.s3.ListBucket],
                            Effect=Allow,
                            Resource=[terraformstatebucket.get_att("Arn")],
                        ),
                        Statement(
                            Action=[awacs.s3.GetObject, awacs.s3.PutObject],
                            Effect=Allow,
                            Resource=[
                                Join("", [terraformstatebucket.get_att("Arn"), "/*"])
                            ],
                        ),
                        Statement(
                            Action=[
                                awacs.dynamodb.GetItem,
                                awacs.dynamodb.PutItem,
                                awacs.dynamodb.DeleteItem,
                            ],
                            Effect=Allow,
                            Resource=[terraformlocktable.get_att("Arn")],
                        ),
                    ],
                ),
            )
        )
        self.template.add_output(
            Output(
                "PolicyArn",
                Description="Managed policy Arn",
                Value=managementpolicy.ref(),
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.context import CfnginContext

    print(  # noqa: T001
        TfState("test", CfnginContext(parameters={"namespace": "test"})).to_json()
    )
