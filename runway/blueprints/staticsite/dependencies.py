#!/usr/bin/env python
"""Module with static website supporting infrastructure."""
from __future__ import print_function

from troposphere import AccountId, Join, Output, s3

import awacs.s3
from awacs.aws import AWSPrincipal, Allow, Policy, Statement

from stacker.blueprints.base import Blueprint
# from stacker.blueprints.variables.types import CFNString


class Dependencies(Blueprint):
    """Stacker blueprint for creating static website buckets."""

    VARIABLES = {}

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        # variables = self.get_variables()
        template.add_version('2010-09-09')
        template.add_description('Static Website - Dependencies')

        # Resources
        awslogbucket = template.add_resource(
            s3.Bucket(
                'AWSLogBucket',
                AccessControl=s3.Private,
                VersioningConfiguration=s3.VersioningConfiguration(
                    Status='Enabled'
                )
            )
        )
        template.add_output(Output(
            'AWSLogBucketName',
            Description='Name of bucket storing AWS logs',
            Value=awslogbucket.ref()
        ))

        template.add_resource(
            s3.BucketPolicy(
                'AllowAWSLogWriting',
                Bucket=awslogbucket.ref(),
                PolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Action=[awacs.s3.PutObject],
                            Effect=Allow,
                            Principal=AWSPrincipal(Join(':',
                                                        ['arn:aws:iam:',
                                                         AccountId,
                                                         'root'])),
                            Resource=[
                                Join('', ['arn:aws:s3:::',
                                          awslogbucket.ref(),
                                          '/*'])
                            ]
                        )
                    ]
                )
            )
        )
        artifacts = template.add_resource(
            s3.Bucket(
                'Artifacts',
                AccessControl=s3.Private,
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
            'ArtifactsBucketName',
            Description='Name of bucket storing artifacts',
            Value=artifacts.ref()
        ))


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from stacker.context import Context
    print(Dependencies('test', Context({"namespace": "test"}), None).to_json())
