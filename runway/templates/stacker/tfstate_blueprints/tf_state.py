#!/usr/bin/env python
"""Module with Terraform state resources."""

from troposphere import (
    Equals, If, Join, NoValue, Or, Output, dynamodb, iam, s3
)

import awacs.dynamodb
import awacs.s3
from awacs.aws import Allow, PolicyDocument, Statement

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString


class TfState(Blueprint):
    """Stacker blueprint for creating Terraform state resources."""

    VARIABLES = {
        'BucketName': {'type': CFNString,
                       'description': '(optional) Name for the S3 bucket',
                       'default': ''},
        'TableName': {'type': CFNString,
                      'description': '(optional) Name for the DynamoDB table',
                      'default': ''}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        self.template.add_version('2010-09-09')
        self.template.add_description('Terraform State Resources')

        # Conditions
        for i in ['BucketName', 'TableName']:
            template.add_condition(
                "%sOmitted" % i,
                Or(Equals(variables[i].ref, ''),
                   Equals(variables[i].ref, 'undefined'))
            )

        # Resources
        terraformlocktable = template.add_resource(
            dynamodb.Table(
                'TerraformStateTable',
                AttributeDefinitions=[
                    dynamodb.AttributeDefinition(
                        AttributeName='LockID',
                        AttributeType='S'
                    )
                ],
                KeySchema=[
                    dynamodb.KeySchema(
                        AttributeName='LockID',
                        KeyType='HASH'
                    )
                ],
                ProvisionedThroughput=dynamodb.ProvisionedThroughput(
                    ReadCapacityUnits=2,
                    WriteCapacityUnits=2
                ),
                TableName=If(
                    'TableNameOmitted',
                    NoValue,
                    variables['TableName'].ref
                )
            )
        )
        template.add_output(Output(
            '%sName' % terraformlocktable.title,
            Description='Name of DynamoDB table for Terraform state',
            Value=terraformlocktable.ref()
        ))

        terraformstatebucket = template.add_resource(
            s3.Bucket(
                'TerraformStateBucket',
                AccessControl=s3.Private,
                BucketName=If(
                    'BucketNameOmitted',
                    NoValue,
                    variables['BucketName'].ref
                ),
                LifecycleConfiguration=s3.LifecycleConfiguration(
                    Rules=[
                        s3.LifecycleRule(
                            NoncurrentVersionExpirationInDays=90,
                            Status='Enabled'
                        )
                    ]
                ),
                VersioningConfiguration=s3.VersioningConfiguration(
                    Status='Enabled'
                )
            )
        )
        template.add_output(Output(
            '%sName' % terraformstatebucket.title,
            Description='Name of bucket storing Terraform state',
            Value=terraformstatebucket.ref()
        ))
        template.add_output(Output(
            '%sArn' % terraformstatebucket.title,
            Description='Arn of bucket storing Terraform state',
            Value=terraformstatebucket.get_att('Arn')
        ))

        managementpolicy = template.add_resource(
            iam.ManagedPolicy(
                'ManagementPolicy',
                Description='Managed policy for Terraform state management.',
                Path='/',
                PolicyDocument=PolicyDocument(
                    Version='2012-10-17',
                    Statement=[
                        # https://www.terraform.io/docs/backends/types/s3.html#s3-bucket-permissions
                        Statement(
                            Action=[awacs.s3.ListBucket],
                            Effect=Allow,
                            Resource=[terraformstatebucket.get_att('Arn')]
                        ),
                        Statement(
                            Action=[awacs.s3.GetObject,
                                    awacs.s3.PutObject],
                            Effect=Allow,
                            Resource=[
                                Join('', [terraformstatebucket.get_att('Arn'),
                                          '/*'])
                            ]
                        ),
                        Statement(
                            Action=[awacs.dynamodb.GetItem,
                                    awacs.dynamodb.PutItem,
                                    awacs.dynamodb.DeleteItem],
                            Effect=Allow,
                            Resource=[terraformlocktable.get_att('Arn')]
                        )
                    ]
                )
            )
        )
        template.add_output(
            Output(
                'PolicyArn',
                Description='Managed policy Arn',
                Value=managementpolicy.ref()
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from stacker.context import Context
    print(TfState('test',
                  Context({'namespace': 'test'}),
                  None).to_json())
