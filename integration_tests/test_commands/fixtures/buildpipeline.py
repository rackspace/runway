#!/usr/bin/env python
"""Module with app build pipeline."""
from __future__ import print_function

from os import path

from troposphere import (
    AWSHelperFn, AccountId, Join, Output, Partition, Region, awslambda,
    codecommit, codebuild, codepipeline, events, iam, s3
)

import awacs.awslambda
import awacs.codebuild
import awacs.codecommit
import awacs.ecr
import awacs.logs
import awacs.s3
import awacs.ssm
from awacs.aws import Allow, PolicyDocument, Statement
from awacs.helpers.trust import make_simple_assume_policy

from stacker.lookups.handlers.file import parameterized_codec
from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString

AWS_LAMBDA_DIR = path.join(path.dirname(path.realpath(__file__)),
                           'aws_lambda')
IAM_ARN_PREFIX = 'arn:aws:iam::aws:policy/service-role/'


class Pipeline(Blueprint):
    """Stacker blueprint for app building components."""

    cleanup_ecr_src = parameterized_codec(
        open(path.join(AWS_LAMBDA_DIR, 'cleanup_ecr.py'), 'r').read(),
        False  # disable base64 encoding
    )

    build_proj_spec = parameterized_codec(
        open(path.join(path.dirname(path.realpath(__file__)),
                       'build_project_buildspec.yml'), 'r').read(),
        False  # disable base64 encoding
    )

    VARIABLES = {
        'ECRCleanupLambdaFunction': {'type': AWSHelperFn,
                                     'description': 'Lambda function code',
                                     'default': cleanup_ecr_src},
        'BuildProjectBuildSpec': {'type': AWSHelperFn,
                                  'description': 'Inline buildspec code',
                                  'default': build_proj_spec},
        'AppPrefix': {'type': CFNString,
                      'description': 'Application prefix (for roles, etc)'},
        'EcrRepoName': {'type': CFNString,
                        'description': 'Name of ECR repo'},
        'RolePermissionsBoundaryName': {'type': CFNString,
                                        'description': 'Roles\' boundary '
                                                       'name'},
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.set_version('2010-09-09')
        template.set_description('App - Build Pipeline')

        # Resources
        boundary_arn = Join('',
                            ['arn:',
                             Partition,
                             ':iam::',
                             AccountId,
                             ':policy/',
                             variables['RolePermissionsBoundaryName'].ref])

        # Repo image limit is 1000 by default; this lambda function will prune
        # old images
        image_param_path = Join('',
                                ['/',
                                 variables['AppPrefix'].ref,
                                 '/current-hash'])
        image_param_arn = Join('',
                               ['arn:',
                                Partition,
                                ':ssm:',
                                Region,
                                ':',
                                AccountId,
                                ':parameter',
                                image_param_path])
        ecr_repo_arn = Join('',
                            ['arn:',
                             Partition,
                             ':ecr:',
                             Region,
                             ':',
                             AccountId,
                             ':repository/',
                             variables['EcrRepoName'].ref])
        cleanuplambdarole = template.add_resource(
            iam.Role(
                'CleanupLambdaRole',
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    'lambda.amazonaws.com'
                ),
                ManagedPolicyArns=[
                    IAM_ARN_PREFIX + 'AWSLambdaBasicExecutionRole'
                ],
                PermissionsBoundary=boundary_arn,
                Policies=[
                    iam.Policy(
                        PolicyName=Join('', [variables['AppPrefix'].ref,
                                             '-ecrcleanup']),
                        PolicyDocument=PolicyDocument(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[awacs.ssm.GetParameter],
                                    Effect=Allow,
                                    Resource=[
                                        image_param_arn
                                    ]
                                ),
                                Statement(
                                    Action=[
                                        awacs.ecr.DescribeImages,
                                        awacs.ecr.BatchDeleteImage
                                    ],
                                    Effect=Allow,
                                    Resource=[ecr_repo_arn]
                                )
                            ]
                        )
                    )
                ]
            )
        )
        cleanupfunction = template.add_resource(
            awslambda.Function(
                'CleanupFunction',
                Description='Cleanup stale ECR images',
                Code=awslambda.Code(
                    ZipFile=variables['ECRCleanupLambdaFunction']
                ),
                Environment=awslambda.Environment(
                    Variables={
                        'ECR_REPO_NAME': variables['EcrRepoName'].ref,
                        'SSM_PARAM': image_param_path
                    }
                ),
                Handler='index.handler',
                Role=cleanuplambdarole.get_att('Arn'),
                Runtime='python3.6',
                Timeout=120
            )
        )
        cleanuprule = template.add_resource(
            events.Rule(
                'CleanupRule',
                Description='Regularly invoke CleanupFunction',
                ScheduleExpression='rate(7 days)',
                State='ENABLED',
                Targets=[
                    events.Target(
                        Arn=cleanupfunction.get_att('Arn'),
                        Id='CleanupFunction'
                    )
                ]
            )
        )
        template.add_resource(
            awslambda.Permission(
                'AllowCWLambdaInvocation',
                FunctionName=cleanupfunction.ref(),
                Action=awacs.awslambda.InvokeFunction.JSONrepr(),
                Principal='events.amazonaws.com',
                SourceArn=cleanuprule.get_att('Arn')
            )
        )

        appsource = template.add_resource(
            codecommit.Repository(
                'AppSource',
                RepositoryName=Join('-',
                                    [variables['AppPrefix'].ref,
                                     'source'])
            )
        )
        for i in ['Name', 'Arn']:
            template.add_output(Output(
                "AppRepo%s" % i,
                Description="%s of app source repo" % i,
                Value=appsource.get_att(i)
            ))

        bucket = template.add_resource(
            s3.Bucket(
                'Bucket',
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
            'PipelineBucketName',
            Description='Name of pipeline bucket',
            Value=bucket.ref()
        ))

        # This list must be kept in sync between the CodeBuild project and its
        # role
        build_name = Join('', [variables['AppPrefix'].ref, '-build'])

        build_role = template.add_resource(
            iam.Role(
                'BuildRole',
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    'codebuild.amazonaws.com'
                ),
                PermissionsBoundary=boundary_arn,
                Policies=[
                    iam.Policy(
                        PolicyName=Join('', [build_name, '-policy']),
                        PolicyDocument=PolicyDocument(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[awacs.s3.GetObject],
                                    Effect=Allow,
                                    Resource=[
                                        Join('',
                                             [bucket.get_att('Arn'),
                                              '/*'])
                                    ]
                                ),
                                Statement(
                                    Action=[awacs.ecr.GetAuthorizationToken],
                                    Effect=Allow,
                                    Resource=['*']
                                ),
                                Statement(
                                    Action=[
                                        awacs.ecr.BatchCheckLayerAvailability,
                                        awacs.ecr.BatchGetImage,
                                        awacs.ecr.CompleteLayerUpload,
                                        awacs.ecr.DescribeImages,
                                        awacs.ecr.GetDownloadUrlForLayer,
                                        awacs.ecr.InitiateLayerUpload,
                                        awacs.ecr.PutImage,
                                        awacs.ecr.UploadLayerPart
                                    ],
                                    Effect=Allow,
                                    Resource=[ecr_repo_arn]
                                ),
                                Statement(
                                    Action=[awacs.ssm.GetParameter,
                                            awacs.ssm.PutParameter],
                                    Effect=Allow,
                                    Resource=[
                                        image_param_arn
                                    ]
                                ),
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
                                                ':log-group:/aws/codebuild/',
                                                build_name
                                            ] + x
                                        ) for x in [[':*'], [':*/*']]
                                    ]
                                )
                            ]
                        )
                    )
                ]
            )
        )

        buildproject = template.add_resource(
            codebuild.Project(
                'BuildProject',
                Artifacts=codebuild.Artifacts(
                    Type='CODEPIPELINE'
                ),
                Environment=codebuild.Environment(
                    ComputeType='BUILD_GENERAL1_SMALL',
                    EnvironmentVariables=[
                        codebuild.EnvironmentVariable(
                            Name='AWS_DEFAULT_REGION',
                            Type='PLAINTEXT',
                            Value=Region
                        ),
                        codebuild.EnvironmentVariable(
                            Name='AWS_ACCOUNT_ID',
                            Type='PLAINTEXT',
                            Value=AccountId
                        ),
                        codebuild.EnvironmentVariable(
                            Name='IMAGE_REPO_NAME',
                            Type='PLAINTEXT',
                            Value=variables['EcrRepoName'].ref
                        ),
                    ],
                    Image='aws/codebuild/docker:18.09.0',
                    Type='LINUX_CONTAINER'
                ),
                Name=build_name,
                ServiceRole=build_role.get_att('Arn'),
                Source=codebuild.Source(
                    Type='CODEPIPELINE',
                    BuildSpec=variables['BuildProjectBuildSpec']
                )
            )
        )

        pipelinerole = template.add_resource(
            iam.Role(
                'PipelineRole',
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    'codepipeline.amazonaws.com'
                ),
                PermissionsBoundary=boundary_arn,
                Policies=[
                    iam.Policy(
                        PolicyName=Join('', [build_name, '-pipeline-policy']),
                        PolicyDocument=PolicyDocument(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Action=[awacs.codecommit.GetBranch,
                                            awacs.codecommit.GetCommit,
                                            awacs.codecommit.UploadArchive,
                                            awacs.codecommit.GetUploadArchiveStatus,  # noqa
                                            awacs.codecommit.CancelUploadArchive],  # noqa
                                    Effect=Allow,
                                    Resource=[appsource.get_att('Arn')]
                                ),
                                Statement(
                                    Action=[awacs.s3.GetBucketVersioning],
                                    Effect=Allow,
                                    Resource=[bucket.get_att('Arn')]
                                ),
                                Statement(
                                    Action=[awacs.s3.GetObject,
                                            awacs.s3.PutObject],
                                    Effect=Allow,
                                    Resource=[
                                        Join('',
                                             [bucket.get_att('Arn'),
                                              '/*'])
                                    ]
                                ),
                                Statement(
                                    Action=[
                                        awacs.codebuild.BatchGetBuilds,
                                        awacs.codebuild.StartBuild
                                    ],
                                    Effect=Allow,
                                    Resource=[
                                        buildproject.get_att('Arn')
                                    ]
                                )
                            ]
                        )
                    )
                ]
            )
        )

        template.add_resource(
            codepipeline.Pipeline(
                'Pipeline',
                ArtifactStore=codepipeline.ArtifactStore(
                    Location=bucket.ref(),
                    Type='S3'
                ),
                Name=build_name,
                RoleArn=pipelinerole.get_att('Arn'),
                Stages=[
                    codepipeline.Stages(
                        Name='Source',
                        Actions=[
                            codepipeline.Actions(
                                Name='CodeCommit',
                                ActionTypeId=codepipeline.ActionTypeId(
                                    Category='Source',
                                    Owner='AWS',
                                    Provider='CodeCommit',
                                    Version='1'
                                ),
                                Configuration={
                                    'RepositoryName': appsource.get_att('Name'),  # noqa
                                    'BranchName': 'master'
                                },
                                OutputArtifacts=[
                                    codepipeline.OutputArtifacts(
                                        Name='CodeCommitRepo'
                                    )
                                ]
                            ),
                        ]
                    ),
                    codepipeline.Stages(
                        Name='Build',
                        Actions=[
                            codepipeline.Actions(
                                Name='Build',
                                ActionTypeId=codepipeline.ActionTypeId(
                                    Category='Build',
                                    Owner='AWS',
                                    Provider='CodeBuild',
                                    Version='1'
                                ),
                                Configuration={
                                    'ProjectName': buildproject.ref()
                                },
                                InputArtifacts=[
                                    codepipeline.InputArtifacts(
                                        Name='CodeCommitRepo'
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from stacker.context import Context
    print(Pipeline('test', Context({"namespace": "test"}), None).to_json())
