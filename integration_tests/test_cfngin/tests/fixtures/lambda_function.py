""" Load dependencies """
from __future__ import print_function

from troposphere import Ref, Join, Sub, Output, awslambda, iam, Export, GetAtt

import awacs.awslambda
import awacs.logs
import awacs.sts
import awacs.dynamodb
from awacs.aws import Allow, Statement, Policy, Principal

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString


class BlueprintClass(Blueprint):
    """Blueprint for creating lambda function."""

    VARIABLES = {
        "Code": {
            "type": awslambda.Code,
            "description": "The troposphere.awslambda.Code object "
                           "returned by the aws lambda hook.",
        },
        "AppName": {
            "type": CFNString,
            "description": "Name of app"
        }
    }

    def create_resources(self):
        """Create the resources."""
        template = self.template
        variables = self.get_variables()
        app_name = variables.get('AppName').ref

        lambda_iam_role = template.add_resource(
            iam.Role(
                'LambdaRole',
                RoleName=Join('-',
                              [app_name,
                               'lambda-role']),
                AssumeRolePolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal('Service',
                                                ['lambda.amazonaws.com'])
                        )
                    ]
                ),
                Path='/service-role/',
                Policies=[
                    iam.Policy(
                        PolicyName=Join('-',
                                        [app_name,
                                         'lambda-policy']),
                        PolicyDocument=Policy(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.logs.CreateLogGroup,
                                        awacs.logs.CreateLogStream,
                                        awacs.logs.PutLogEvents
                                    ],
                                    Effect=Allow,
                                    Resource=['arn:aws:logs:*:*:*'],
                                    Sid='WriteLogs'
                                )
                            ]
                        )
                    )
                ]
            )
        )

        lambda_function = template.add_resource(
            awslambda.Function(
                'LambdaFunction',
                Code=variables['Code'],
                Handler='index.handler',
                Role=GetAtt(lambda_iam_role, 'Arn'),
                Runtime='python3.6',
                Timeout=30,
                MemorySize=128,
                FunctionName=Join('-',
                                   [app_name,
                                   'integrationtest'])
            )
        )

        template.add_output(
            Output(
                lambda_iam_role.title,
                Description='Lambda Role',
                Export=Export(Sub('${AWS::StackName}-%s' % lambda_iam_role.title)),  # nopep8 pylint: disable=C0301
                Value=Ref(lambda_iam_role)
            )
        )
        template.add_output(
            Output(
                lambda_function.title,
                Description='Lambda Function',
                Export=Export(Sub('${AWS::StackName}-%s' % lambda_function.title)),  # nopep8 pylint: disable=C0301
                Value=GetAtt(lambda_function, 'Arn')
            )
        )
        template.add_output(
            Output(
                lambda_function.title + 'Name',
                Description='Lambda Function Name',
                Export=Export(Sub('${AWS::StackName}-%sName' % lambda_function.title)),  # nopep8 pylint: disable=C0301
                Value=Ref(lambda_function)
            )
        )

    def create_template(self):
        self.template.add_version('2010-09-09')
        self.template.add_description('Test Lambda'
                                      ' - {0}'.format('1.0.0'))
        self.create_resources()
