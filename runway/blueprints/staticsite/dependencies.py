#!/usr/bin/env python
"""Module with static website supporting infrastructure."""
from __future__ import print_function

import logging

import awacs.s3
from awacs.aws import Allow, AWSPrincipal, Policy, Statement
from troposphere import AccountId, Join, Output, cognito, s3

from runway.cfngin.blueprints.base import Blueprint

LOGGER = logging.getLogger(__name__)


class Dependencies(Blueprint):
    """Stacker blueprint for creating static website buckets."""

    VARIABLES = {
        'AuthAtEdge': {
            'type': bool,
            'default': False,
            'description': 'Utilizing Authorization @ Edge'
        },
        'CreateUserPool': {
            'type': bool,
            'default': False,
            'description': 'Whether a User Pool should be created for the project'
        },
        'UserPoolId': {
            'type': str,
            'default': '',
            'description': 'User Pool ID for Authorization @ Edge'
        },
        'OAuthScopes': {
            'type': list,
            'default': [
                'phone',
                'email',
                'profile',
                'openid',
                'aws.cognito.signin.user.admin'
            ],
            'description': 'The allowed scopes for OAuth validation'
        }
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.set_version('2010-09-09')
        template.set_description('Static Website - Dependencies')

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

        if variables['AuthAtEdge']:
            callbacks = self.context.hook_data['aae_callback_url_retriever']['callback_urls']

            user_pool_id = variables['UserPoolId']

            if variables['CreateUserPool']:
                user_pool = template.add_resource(
                    cognito.UserPool("AuthAtEdgeUserPool")
                )

                user_pool_id = user_pool.ref()

                template.add_output(Output(
                    'AuthAtEdgeUserPoolId',
                    Description='Cognito User Pool App Client for Auth @ Edge',
                    Value=user_pool_id
                ))

            client = template.add_resource(
                cognito.UserPoolClient(
                    "AuthAtEdgeClient",
                    AllowedOAuthFlows=['code'],
                    CallbackURLs=callbacks,
                    UserPoolId=user_pool_id,
                    AllowedOAuthScopes=variables['OAuthScopes']
                )
            )

            template.add_output(Output(
                'AuthAtEdgeClient',
                Description='Cognito User Pool App Client for Auth @ Edge',
                Value=client.ref()
            ))


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.cfngin.context import Context
    print(Dependencies('test', Context({"namespace": "test"}), None).to_json())
