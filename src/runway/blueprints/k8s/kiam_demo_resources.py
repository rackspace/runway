#!/usr/bin/env python
"""Module with AWS resources for kiam demo app."""
from __future__ import print_function

import awacs.ssm
import awacs.sts
from awacs.aws import Allow, Principal, Statement, PolicyDocument
from troposphere import AccountId, Join, Partition, Region, iam, ssm
from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString


class KiamDemo(Blueprint):
    """Stacker blueprint for creating AWS resources for kiam demo app."""

    VARIABLES = {
        'Namespace': {'type': CFNString,
                      'description': 'CloudFormation namespace (i.e. logical '
                                     'environment).'},
        'RoleName': {'type': CFNString,
                     'description': 'IAM role name.'}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.add_version('2010-09-09')
        template.add_description('kiam demo app resources')

        # Resources
        param = ['/', variables['Namespace'].ref, '/kiam-demo-app/param']

        template.add_resource(
            ssm.Parameter(
                'Param',
                Description='Sample parameter for k8s app to query',
                Name=Join('', param),
                Type='String',
                Value='Accessed via a namespace/pod-authorized role!'
            )
        )

        template.add_resource(
            iam.Role(
                'Role',
                RoleName=variables['RoleName'].ref,
                AssumeRolePolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal(
                                'AWS',
                                Join(':',
                                     ['arn',
                                      Partition,
                                      'iam:',
                                      AccountId,
                                      'root'])
                            )
                        )
                    ]
                ),
                Policies=[
                    iam.Policy(
                        PolicyName='allow-param-retrieval',
                        PolicyDocument=PolicyDocument(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[awacs.ssm.GetParameter],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            '',
                                            ['arn:',
                                             Partition,
                                             ':ssm:',
                                             Region,
                                             ':',
                                             AccountId,
                                             ':parameter'] + param
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                ]
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from stacker.context import Context
    print(KiamDemo('test', Context({"namespace": "test"}), None).to_json())
