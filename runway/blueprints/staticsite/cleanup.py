#!/usr/bin/env python
"""Cleanup Stack.

Responsible for cleaning up the remaining orphaned resources created
by the primary stack.
"""
from __future__ import print_function

import json
import logging
import os
from typing import Any, Dict, Union  # pylint: disable=unused-import

import awacs.awslambda
import awacs.cloudformation
import awacs.iam
import awacs.logs
from awacs.aws import Allow, PolicyDocument, Statement
from awacs.helpers.trust import make_simple_assume_policy
from troposphere import (
    AccountId,
    Join,
    NoValue,
    Output,
    Partition,
    Region,
    StackName,
    Sub,
    awslambda,
    iam,
    stepfunctions,
)

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.util import read_value_from_path

LOGGER = logging.getLogger("runway")


class Cleanup(Blueprint):
    """Cleanup Stack."""

    VARIABLES = {
        "DisableCloudFront": {
            "type": bool,
            "default": False,
            "description": "Whether to disable CF",
        },
        "RoleBoundaryArn": {
            "type": str,
            "default": "",
            "description": "(Optional) IAM Role permissions "
            "boundary applied to any created "
            "roles.",
        },
        "function_arns": {
            "type": list,
            "default": [],
            "description": "List of function ARNs that need to " "be removed.",
        },
        "stack_name": {
            "type": str,
            "default": "",
            "description": "The name of the current stack",
        },
    }

    @property
    def cf_enabled(self):
        # type: () -> bool
        """CloudFront enabled conditional."""
        return not self.get_variables().get("DisableCloudFront", False)

    @property
    def role_boundary_specified(self):
        # type: () -> bool
        """IAM Role Boundary specified conditional."""
        return self.get_variables()["RoleBoundaryArn"] != ""

    def create_template(self):
        # type: () -> None
        """Create template (main function called by Stacker)."""
        self.template.set_version("2010-09-09")
        self.template.set_description("Static Website Cleanup - StateMachine")
        if not self.cf_enabled:
            return

        self._get_replicated_lambda_state_machine()

    def _get_replicated_lambda_remover_lambda(self):
        # type: () -> Dict[str, Any]
        res = {}
        variables = self.get_variables()
        res["role"] = self.template.add_resource(
            iam.Role(
                "ReplicatedLambdaRemoverRole",
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    "lambda.amazonaws.com"
                ),
                PermissionsBoundary=(
                    variables["RoleBoundaryArn"]
                    if self.role_boundary_specified
                    else NoValue
                ),
                Policies=[
                    iam.Policy(
                        PolicyName="LambdaLogCreation",
                        PolicyDocument=PolicyDocument(
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
                                                ":logs:*:",
                                                AccountId,
                                                ":log-group:/aws/lambda/",
                                                StackName,
                                                "-ReplicatedLambdaRemover-*",
                                            ],
                                        )
                                    ],
                                )
                            ],
                        ),
                    ),
                    iam.Policy(
                        PolicyName="DeleteLambda",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[awacs.awslambda.DeleteFunction],
                                    Effect=Allow,
                                    Resource=self.get_variables()["function_arns"],
                                )
                            ],
                        ),
                    ),
                ],
            )
        )

        self.template.add_output(
            Output(
                "ReplicatedLambdaRemoverRole",
                Description="The name of the Replicated Lambda Remover Role",
                Value=res["role"].ref(),
            )
        )

        res["function"] = self.template.add_resource(
            awslambda.Function(
                "ReplicatedLambdaRemover",
                Code=awslambda.Code(
                    ZipFile=read_value_from_path(
                        "file://"
                        + os.path.join(
                            os.path.dirname(__file__),
                            "templates/replicated_lambda_remover.template.py",
                        )
                    )
                ),
                Description="Checks for Replicated Lambdas created during the main stack and "
                "deletes them when they are ready.",
                Handler="index.handler",
                Role=res["role"].get_att("Arn"),
                Runtime="python3.7",
            )
        )

        self.template.add_output(
            Output(
                "ReplicatedLambdaRemoverArn",
                Description="The ARN of the Replicated Function",
                Value=res["function"].get_att("Arn"),
            )
        )

        return res

    def _get_self_destruct(self, replicated_lambda_remover):
        # type: (Dict[str, Union[awslambda.Function, Any]]) -> Dict[str, Any]
        res = {}
        variables = self.get_variables()

        res["role"] = self.template.add_resource(
            iam.Role(
                "SelfDestructRole",
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    "lambda.amazonaws.com"
                ),
                PermissionsBoundary=(
                    variables["RoleBoundaryArn"]
                    if self.role_boundary_specified
                    else NoValue
                ),
                Policies=[
                    iam.Policy(
                        PolicyName="LambdaLogCreation",
                        PolicyDocument=PolicyDocument(
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
                                                ":logs:*:",
                                                AccountId,
                                                ":log-group:/aws/lambda/",
                                                StackName,
                                                "-SelfDestruct-*",
                                            ],
                                        )
                                    ],
                                )
                            ],
                        ),
                    ),
                    iam.Policy(
                        PolicyName="DeleteStateMachine",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[awacs.states.DeleteStateMachine],
                                    Effect=Allow,
                                    Resource=[
                                        # StateMachine
                                        Join(
                                            "",
                                            [
                                                "arn:",
                                                Partition,
                                                ":states:",
                                                Region,
                                                ":",
                                                AccountId,
                                                ":stateMachine:StaticSiteCleanup-",
                                                variables["stack_name"],
                                            ],
                                        )
                                    ],
                                )
                            ],
                        ),
                    ),
                    iam.Policy(
                        PolicyName="DeleteRolesAndPolicies",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.iam.DeleteRolePolicy,
                                        awacs.iam.DeleteRole,
                                    ],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            "",
                                            [
                                                "arn:",
                                                Partition,
                                                ":iam::",
                                                AccountId,
                                                ":role/",
                                                StackName,
                                                "-*",
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ),
                    iam.Policy(
                        PolicyName="DeleteLambdas",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[awacs.awslambda.DeleteFunction],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            "",
                                            [
                                                "arn:",
                                                Partition,
                                                ":lambda:",
                                                Region,
                                                ":",
                                                AccountId,
                                                ":function:%s-SelfDestruct-*"
                                                % (variables["stack_name"]),
                                            ],
                                        ),
                                        replicated_lambda_remover["function"].get_att(
                                            "Arn"
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ),
                    iam.Policy(
                        PolicyName="DeleteStack",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[awacs.cloudformation.DeleteStack],
                                    Effect=Allow,
                                    Resource=[
                                        Join(
                                            "",
                                            [
                                                "arn:",
                                                Partition,
                                                ":cloudformation:",
                                                Region,
                                                ":",
                                                AccountId,
                                                ":stack/%s/*"
                                                % (variables["stack_name"]),
                                            ],
                                        )
                                    ],
                                )
                            ],
                        ),
                    ),
                ],
            )
        )

        self.template.add_output(
            Output(
                "SelfDestructLambdaRole",
                Description="The name of the Self Destruct Role",
                Value=res["role"].ref(),
            )
        )

        res["function"] = self.template.add_resource(
            awslambda.Function(
                "SelfDestruct",
                Code=awslambda.Code(
                    ZipFile=read_value_from_path(
                        "file://"
                        + os.path.join(
                            os.path.dirname(__file__),
                            "templates/self_destruct.template.py",
                        )
                    )
                ),
                Description="Issues a Delete Stack command to the Cleanup stack",
                Handler="index.handler",
                Role=res["role"].get_att("Arn"),
                Runtime="python3.7",
            )
        )

        self.template.add_output(
            Output(
                "SelfDestructLambdaArn",
                Description="The ARN of the Replicated Function",
                Value=res["function"].get_att("Arn"),
            )
        )

        return res

    def _get_replicated_lambda_state_machine_role(
        self,
        remover_function,  # type: Dict[str, Union[awslambda.Function, iam.Role, Any]]
        self_destruct_function,  # type: Dict[str, Union[awslambda.Function, iam.Role, Any]]
    ):
        # type (...) -> iam.Role
        variables = self.get_variables()
        entity = Join(".", ["states", Region, "amazonaws.com"])

        return self.template.add_resource(
            iam.Role(
                "StateMachineRole",
                AssumeRolePolicyDocument=make_simple_assume_policy(entity),
                PermissionsBoundary=(
                    variables["RoleBoundaryArn"]
                    if self.role_boundary_specified
                    else NoValue
                ),
                Policies=[
                    iam.Policy(
                        PolicyName="InvokeLambda",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[awacs.awslambda.InvokeFunction],
                                    Effect=Allow,
                                    Resource=[
                                        remover_function.get_att("Arn"),
                                        self_destruct_function.get_att("Arn"),
                                    ],
                                )
                            ],
                        ),
                    )
                ],
            )
        )

    def _get_replicated_lambda_state_machine(self):
        # type(...) -> stepfunctions.StateMachine
        replicated_lambda_remover = self._get_replicated_lambda_remover_lambda()
        self_destruct = self._get_self_destruct(replicated_lambda_remover)
        role = self._get_replicated_lambda_state_machine_role(
            replicated_lambda_remover["function"], self_destruct["function"]
        )

        state_machine = self.template.add_resource(
            stepfunctions.StateMachine(
                "StaticSiteCleanupStateMachine",
                StateMachineName="StaticSiteCleanup-%s"
                % (self.get_variables()["stack_name"]),
                RoleArn=role.get_att("Arn"),
                DefinitionString=Sub(
                    json.dumps(
                        {
                            "Comment": "Clean leftover artifacts from StaticSite build",
                            "StartAt": "DeleteLambdas",
                            "States": {
                                "DeleteLambdas": {
                                    "Type": "Task",
                                    "Resource": "${delete_lambdas_arn}",
                                    "Next": "Deleted",
                                },
                                "Deleted": {
                                    "Type": "Choice",
                                    "Choices": [
                                        {
                                            "Variable": "$.deleted",
                                            "BooleanEquals": True,
                                            "Next": "SelfDestruct",
                                        },
                                        {
                                            "Variable": "$.deleted",
                                            "BooleanEquals": False,
                                            "Next": "Halt",
                                        },
                                    ],
                                },
                                "Halt": {
                                    "Type": "Wait",
                                    "Seconds": 300,
                                    "Next": "DeleteLambdas",
                                },
                                "SelfDestruct": {
                                    "Type": "Task",
                                    "Resource": "${self_destruct_arn}",
                                    "Next": "DeletionComplete",
                                },
                                "DeletionComplete": {"Type": "Succeed"},
                            },
                        }
                    ),
                    {
                        "delete_lambdas_arn": replicated_lambda_remover[
                            "function"
                        ].get_att("Arn"),
                        "self_destruct_arn": self_destruct["function"].get_att("Arn"),
                    },
                ),
            )
        )

        self.template.add_output(
            Output(
                "ReplicatedFunctionRemoverStateMachineArn",
                Description="The ARN of the Replicated Function Remover State Machine",
                Value=state_machine.ref(),
            )
        )
        return state_machine
