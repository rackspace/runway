#!/usr/bin/env python
"""Module with CodeBuild project."""
import sys
from os.path import dirname, realpath

from awacs.helpers.trust import make_simple_assume_policy
from troposphere import codebuild, iam

from integration_tests.runner import Runner
from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString

from .iam_policy_builder import IAMPolicyBuilder

ROOT_DIR = dirname(dirname(dirname(dirname(dirname(realpath(__file__))))))
sys.path.insert(0, ROOT_DIR)


# The github accounts that are allowed to trigger the
# build tests
# (ids available via https://api.github.com/users/USERNAME)
GITHUB_ACCOUNT_IDS = [
    149096,  # Tolga
    1806418,  # Troy
    23145462,  # Kyle
    627555,  # Craig
    395624   # Edgar
]

ALT_TESTING_ACCOUNT_ID = '395611358874'
IAM_POLICY_BUILDER = IAMPolicyBuilder()


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

        def add_test_resources(test_name):
            """Add the resources for the given test."""
            codebuild_role = template.add_resource(
                iam.Role(
                    'CodeBuildRole{}'.format(test_name),
                    AssumeRolePolicyDocument=make_simple_assume_policy(
                        'codebuild.amazonaws.com'
                    ),
                    Policies=IAM_POLICY_BUILDER.build(test_name)
                )
            )

            template.add_resource(codebuild.Project(
                f'RunwayIntegrationTest{test_name}',
                Artifacts=codebuild.Artifacts(
                    Type='NO_ARTIFACTS'
                ),
                Description=f'{test_name} runway integration tests',
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
                            Value=test_name.lower()
                        ),
                        codebuild.EnvironmentVariable(
                            # Disable emojis in output.
                            Name='PIPENV_HIDE_EMOJIS',
                            Type='PLAINTEXT',
                            Value='1'
                        ),
                        codebuild.EnvironmentVariable(
                            # disable terminal spinner.
                            Name='PIPENV_NOSPIN',
                            Type='PLAINTEXT',
                            Value='1'
                        ),
                        codebuild.EnvironmentVariable(
                            # Pipenv automatically assumes “yes” at all prompts.
                            Name='PIPENV_YES',
                            Type='PLAINTEXT',
                            Value='1'
                        )
                    ],
                    Image='aws/codebuild/standard:2.0',
                    Type='LINUX_CONTAINER'
                ),
                Name=f'runway-int-test-{test_name}',
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
            ))

        runner = Runner(use_abs=True)

        # create the necessary resources for each test
        for test in runner.available_tests:
            add_test_resources(test.__name__)


if __name__ == "__main__":
    from runway.cfngin.context import Context
    print(CodeBuild('test', Context({"namespace": "test"}), None).to_json())
