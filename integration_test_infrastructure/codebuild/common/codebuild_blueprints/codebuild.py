#!/usr/bin/env python
"""Module with CodeBuild project."""
from __future__ import print_function
from os.path import dirname, realpath
import sys

from troposphere import (
    AccountId, Join, Partition, Region, iam, codebuild, Sub
)

import awacs.cloudformation
import awacs.codebuild
import awacs.dynamodb
import awacs.logs
import awacs.s3
import awacs.sts

from awacs.aws import Action, Allow, PolicyDocument, Statement
from awacs.helpers.trust import make_simple_assume_policy

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString

root_dir = dirname(dirname(dirname(dirname(dirname(realpath(__file__))))))
sys.path.insert(0, root_dir)

from integration_tests.runner import Runner  # noqa pylint: disable=wrong-import-position

# The github accounts that are allowed to trigger the
# build tests
# (ids available via https://api.github.com/users/USERNAME)
GITHUB_ACCOUNT_IDS = [
    149096,  # Tolga
    1806418,  # Troy
    23145462,  # Kyle
    627555  # Craig
]

ALT_TESTING_ACCOUNT_ID = '395611358874'


class CodeBuild(Blueprint):
    """Stacker blueprint for CodeBuild project."""

    VARIABLES = {
        'EnvironmentName': {'type': CFNString,
                            'description': 'Name of environment'},
        'GitHubUrl': {'type': CFNString,
                      'description': 'URL to GitHub repository'}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.set_version('2010-09-09')
        template.set_description('Runway CodeBuild Project')

        # Resources
        deploy_name_list = ['runway-int-test-']

        # This must match what is in the the Terraform
        # integration tests. This corresponds to the template listed in
        # integration_tests\test_terraform\tf_state.cfn
        test_suite_prefix = 'testsuite-tf-state'
        codebuild_role = template.add_resource(
            iam.Role(
                'CodeBuildRole',
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    'codebuild.amazonaws.com'
                ),
                # todo: drop this broad access in favor of more narrow
                # permissions (will mean identifying all the needed
                # permissions across all tests)
                ManagedPolicyArns=[
                    'arn:aws:iam::aws:policy/AdministratorAccess'
                ],
                Policies=[
                    iam.Policy(
                        PolicyName=Join('', deploy_name_list + ['-policy']),
                        PolicyDocument=PolicyDocument(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.logs.CreateLogGroup,
                                        awacs.logs.CreateLogStream,
                                        awacs.logs.PutLogEvents
                                    ],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            '',
                                            [
                                                'arn:',
                                                Partition,
                                                ':logs:',
                                                Region,
                                                ':',
                                                AccountId,
                                                ':log-group:/aws/codebuild/'
                                            ] + deploy_name_list + [
                                                '*'
                                            ] + x
                                        ) for x in [[':*'], [':*/*']]
                                    ]
                                ),
                                Statement(
                                    Action=[awacs.sts.AssumeRole],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            '',
                                            ['arn:', Partition, ':iam::',
                                             ALT_TESTING_ACCOUNT_ID,
                                             ':role/runway-integration-test-role-',  # noqa
                                             variables['EnvironmentName'].ref])
                                    ]
                                ),
                                Statement(
                                    Action=[Action('cloudformation', '*')],
                                    Effect=Allow,
                                    Resource=[
                                        Join(':', ['arn', Partition, 'cloudformation',
                                                   Region, AccountId,
                                                   Sub('stack/${prefix}/*',
                                                       {'prefix': test_suite_prefix})])
                                    ]
                                ),
                                Statement(
                                    Action=[Action('dynamodb', '*')],
                                    Effect=Allow,
                                    Resource=[
                                        Join(':', ['arn', Partition, 'dynamodb',
                                                   Region, AccountId,
                                                   Sub('table/${prefix}-*',
                                                       {'prefix': test_suite_prefix})])
                                    ]
                                ),
                                Statement(
                                    Action=[Action('s3', '*')],
                                    Effect=Allow,
                                    Resource=[
                                        Join(':', ['arn', Partition,
                                                   Sub('s3:::${prefix}',
                                                       {'prefix': test_suite_prefix})]),
                                        Join(':', ['arn', Partition,
                                                   Sub('s3:::${prefix}/*',
                                                       {'prefix': test_suite_prefix})])
                                    ]
                                ),
                                Statement(
                                    Action=[Action('sqs', '*')],
                                    Effect=Allow,
                                    Resource=[
                                        Join(':', ['arn', Partition, 'sqs', Region, AccountId,
                                                   'terraform-*'])
                                    ]
                                )
                            ]
                        )
                    )
                ]
            )
        )

        def generate_codebuild_resource(name):
            return codebuild.Project(
                f'RunwayIntegrationTest{name}',
                Artifacts=codebuild.Artifacts(
                    Type='NO_ARTIFACTS'
                ),
                Description=f'{name} runway integration tests',
                Environment=codebuild.Environment(
                    ComputeType='BUILD_GENERAL1_SMALL',
                    EnvironmentVariables=[
                        codebuild.EnvironmentVariable(
                            Name='DEPLOY_ENVIRONMENT',
                            Type='PLAINTEXT',
                            Value=variables['EnvironmentName'].ref
                        ),
                        codebuild.EnvironmentVariable(
                            Name='TEST_TO_RUN',
                            Type='PLAINTEXT',
                            Value=name.lower()
                        )
                    ],
                    Image='aws/codebuild/standard:2.0',
                    Type='LINUX_CONTAINER'
                ),
                Name=f'runway-int-test-{name}',
                ServiceRole=codebuild_role.get_att('Arn'),
                Source=codebuild.Source(
                    Type='GITHUB',
                    Location=variables['GitHubUrl'].ref
                ),
                Triggers=codebuild.ProjectTriggers(
                    Webhook=True,
                    FilterGroups=[
                        [
                            codebuild.WebhookFilter(
                                Type='ACTOR_ACCOUNT_ID',
                                Pattern='|'.join(str(x) for x in GITHUB_ACCOUNT_IDS)
                            ),
                            codebuild.WebhookFilter(
                                Type='EVENT',
                                Pattern='PULL_REQUEST_CREATED,'
                                        'PULL_REQUEST_UPDATED,'
                                        'PULL_REQUEST_REOPENED'
                            ),
                            codebuild.WebhookFilter(
                                Type='BASE_REF',
                                Pattern='^refs/heads/release$'
                            ),
                            codebuild.WebhookFilter(
                                Type='HEAD_REF',
                                Pattern='^refs/heads/master$'
                            )
                        ]
                    ]
                )
            )

        runner = Runner(use_abs=True)

        for test in runner.available_tests:
            template.add_resource(generate_codebuild_resource(test.__name__))


if __name__ == "__main__":
    from stacker.context import Context
    print(CodeBuild('test', Context({"namespace": "test"}), None).to_json())
