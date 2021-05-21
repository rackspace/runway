"""Blueprint for creating a Lambda Function."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Final

import awacs.awslambda
import awacs.dynamodb
import awacs.logs
import awacs.sts
from awacs.aws import Allow, Policy, Principal, Statement
from troposphere import AccountId, GetAtt, Join, Partition, Region, awslambda, iam

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString
from runway.compat import cached_property

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class LambdaFunction(Blueprint):
    """Blueprint for creating a Lambda Function."""

    VARIABLES: Final[Dict[str, BlueprintVariableTypeDef]] = {
        "AppName": {"type": str, "description": "Name of app"},
        "Code": {
            "type": awslambda.Code,
            "description": "The troposphere.awslambda.Code object "
            "returned by the aws lambda hook.",
        },
        "Entrypoint": {
            "type": CFNString,
            "description": "Lambda function entrypoint.",
            "default": "index.handler",
        },
        "PermissionsBoundary": {
            "type": CFNString,
            "description": "Permissions boundary to apply to the Role",
        },
    }

    @cached_property
    def app_name(self) -> str:
        """Name of the application."""
        return self.variables["AppName"]

    @cached_property
    def iam_role(self) -> iam.Role:
        """IAM role attached to the Lambda Function."""
        role = iam.Role(
            "LambdaRole",
            template=self.template,
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
            PermissionsBoundary=self.variables["PermissionsBoundary"].ref,
            Policies=[
                iam.Policy(
                    PolicyName=f"{self.app_name}-lambda-policy",
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
                                            f"{self.app_name}-*",
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
        self.add_output(role.title, role.ref())
        return role

    @cached_property
    def lambda_function(self) -> awslambda.Function:
        """AWS Lambda Function."""
        func = awslambda.Function(
            "LambdaFunction",
            template=self.template,
            Code=self.variables["Code"],
            Handler=self.variables["Entrypoint"].ref,
            Role=GetAtt(self.iam_role, "Arn"),
            Runtime="python3.8",
            Timeout=30,
            MemorySize=128,
            FunctionName=self.context.get_fqn(self.app_name),
        )
        self.add_output(func.title, func.ref())
        self.add_output(f"{func.title}Arn", func.get_att("Arn"))
        return func

    def create_template(self) -> None:
        """Create template."""
        self.template.add_version("2010-09-09")
        self.template.add_description("Test Lambda")
        self.iam_role  # pylint: disable=pointless-statement
        self.lambda_function  # pylint: disable=pointless-statement
