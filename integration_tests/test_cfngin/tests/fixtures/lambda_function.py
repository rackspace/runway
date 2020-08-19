"""Load dependencies."""
import awacs.awslambda
import awacs.dynamodb
import awacs.logs
import awacs.sts
from awacs.aws import Allow, Policy, Principal, Statement
from troposphere import (
    AccountId,
    Export,
    GetAtt,
    Join,
    Output,
    Partition,
    Ref,
    Region,
    Sub,
    awslambda,
    iam,
)

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString


class BlueprintClass(Blueprint):
    """Blueprint for creating lambda function."""

    VARIABLES = {
        "Code": {
            "type": awslambda.Code,
            "description": "The troposphere.awslambda.Code object "
            "returned by the aws lambda hook.",
        },
        "AppName": {"type": CFNString, "description": "Name of app"},
        "Entrypoint": {
            "type": CFNString,
            "description": "Lambda function entrypoint.",
            "default": "index.handler",
        },
    }

    def create_resources(self):
        """Create the resources."""
        template = self.template
        variables = self.get_variables()
        app_name = variables["AppName"].ref

        lambda_iam_role = template.add_resource(
            iam.Role(
                "LambdaRole",
                RoleName=Join("-", [app_name, "lambda-role"]),
                AssumeRolePolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal("Service", ["lambda.amazonaws.com"]),
                        )
                    ],
                ),
                Path="/service-role/",
                Policies=[
                    iam.Policy(
                        PolicyName=Join("-", [app_name, "lambda-policy"]),
                        PolicyDocument=Policy(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.logs.CreateLogGroup,
                                        awacs.logs.CreateLogStream,
                                        awacs.logs.PutLogEvents,
                                    ],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            "",
                                            [
                                                "arn:",
                                                Partition,
                                                ":logs:",
                                                Region,
                                                ":",
                                                AccountId,
                                                ":log-group:/aws/lambda/",
                                                app_name,
                                                "-*",
                                            ],
                                        )
                                    ],
                                    Sid="WriteLogs",
                                )
                            ],
                        ),
                    )
                ],
            )
        )

        lambda_function = template.add_resource(
            awslambda.Function(
                "LambdaFunction",
                Code=variables["Code"],
                Handler=variables["Entrypoint"].ref,
                Role=GetAtt(lambda_iam_role, "Arn"),
                Runtime="python3.6",
                Timeout=30,
                MemorySize=128,
                FunctionName=Join("-", [app_name, "integrationtest"]),
            )
        )

        template.add_output(
            Output(
                lambda_iam_role.title,
                Description="Lambda Role",
                Export=Export(Sub("${AWS::StackName}-%s" % lambda_iam_role.title)),
                Value=Ref(lambda_iam_role),
            )
        )
        template.add_output(
            Output(
                lambda_function.title,
                Description="Lambda Function",
                Export=Export(Sub("${AWS::StackName}-%s" % lambda_function.title)),
                Value=GetAtt(lambda_function, "Arn"),
            )
        )
        template.add_output(
            Output(
                lambda_function.title + "Name",
                Description="Lambda Function Name",
                Export=Export(Sub("${AWS::StackName}-%sName" % lambda_function.title)),
                Value=Ref(lambda_function),
            )
        )

    def create_template(self):
        """Create template."""
        self.template.add_version("2010-09-09")
        self.template.add_description("Test Lambda" " - {0}".format("1.0.0"))
        self.create_resources()
