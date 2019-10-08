#!/usr/bin/env python
"""Module with IAM role."""
from __future__ import print_function

from troposphere import Join, iam

import awacs.sts

from awacs.aws import Allow, PolicyDocument, Principal, Statement

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString

TESTING_ACCOUNT_ID = '523485371024'


class CrossAccountRole(Blueprint):
    """Stacker blueprint for IAM role."""

    VARIABLES = {
        'EnvironmentName': {'type': CFNString,
                            'description': 'Name of environment'}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.set_version('2010-09-09')
        template.set_description('Runway Integration Testing - IAM Role')

        # Resources
        template.add_resource(
            iam.Role(
                'CodeBuildRole',
                AssumeRolePolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal(
                                'AWS',
                                TESTING_ACCOUNT_ID
                            )
                        )
                    ]
                ),
                Description='Role used for cross account testing in runway',
                ManagedPolicyArns=[
                    'arn:aws:iam::aws:policy/AdministratorAccess'
                ],
                RoleName=Join('-', ['runway-integration-test-role',
                                    variables['EnvironmentName'].ref])
            )
        )


if __name__ == "__main__":
    from stacker.context import Context
    print(CrossAccountRole('test', Context({"namespace": "test"}), None).to_json())
