"""Blueprint for IAM permission boundary that prevents privilege escalation.

https://aws.amazon.com/premiumsupport/knowledge-center/iam-permission-boundaries/

"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict, List, Union

import awacs.iam
import awacs.sts
from awacs.aws import (
    Action,
    Allow,
    Condition,
    Deny,
    PolicyDocument,
    Statement,
    StringEquals,
    StringNotEquals,
)
from troposphere import Sub
from troposphere.iam import ManagedPolicy

from runway.cfngin.blueprints.base import Blueprint
from runway.compat import cached_property

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class AdminPreventPrivilegeEscalation(Blueprint):
    """Blueprint for IAM permission boundary that prevents privilege escalation."""

    DESCRIPTION: ClassVar[str] = "Permission boundary for admin users."
    POLICY_NAME: ClassVar[str] = "AdminPreventPrivilegeEscalation"
    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "ApprovedPermissionBoundaries": {
            "default": [],
            "description": "List of policy names (not ARNs) that are approved to "
            "be attached to roles and users.",
            "type": list,
        },
        "DenyAssumeRoleNotResources": {
            "default": [],
            "description": "List of IAM Role ARNs that can be assumed.",
            "type": list,
        },
    }

    @cached_property
    def namespace(self) -> str:
        """Stack namespace."""
        return self.context.namespace

    @cached_property
    def approved_boundary_policies(self) -> List[Sub]:
        """List of approved permission boundary policies."""
        tmp = [self.policy_arn]
        for policy_name in self.variables["ApprovedPermissionBoundaries"]:
            tmp.append(
                Sub(
                    f"arn:${{AWS::Partition}}:iam::${{AWS::AccountId}}:policy/{policy_name}"
                )
            )
        return tmp

    @cached_property
    def deny_assume_role_not_resources(self) -> List[Union[str, Sub]]:
        """List of IAM Role ARNs that can be assumed."""
        tmp: List[Union[str, Sub]] = [
            Sub(
                f"arn:${{AWS::Partition}}:iam::${{AWS::AccountId}}:role/{self.namespace}-*"
            )
        ]
        for arn in self.variables["DenyAssumeRoleNotResources"]:
            tmp.append(arn)
        return tmp

    @property
    def policy_arn(self) -> Sub:
        """ARN of the IAM policy that will be created."""
        return Sub(
            f"arn:${{AWS::Partition}}:iam::${{AWS::AccountId}}:policy/{self.POLICY_NAME}"
        )

    @cached_property
    def statement_allow_admin_access(self) -> Statement:
        """Statement to allow admin access."""
        return Statement(
            Action=[Action("*")], Effect=Allow, Resource=["*"], Sid="AllowAdminAccess"
        )

    @cached_property
    def statement_deny_alter_boundary_policy(self) -> Statement:
        """Statement to deny alteration of this permission boundary policy."""
        return Statement(
            Action=[
                awacs.iam.CreatePolicyVersion,
                awacs.iam.DeletePolicy,
                awacs.iam.DeletePolicyVersion,
                awacs.iam.SetDefaultPolicyVersion,
            ],
            Effect=Deny,
            Resource=[self.policy_arn],
            Sid="DenyBoundaryPolicyAlteration",
        )

    @cached_property
    def statement_deny_assume_role_not_resource(self) -> Statement:
        """Statement to deny AssumeRole if NotResource."""
        return Statement(
            Action=[
                awacs.sts.AssumeRole,
                awacs.sts.AssumeRoleWithSAML,
                awacs.sts.AssumeRoleWithWebIdentity,
            ],
            Effect=Deny,
            NotResource=self.deny_assume_role_not_resources,
            Sid="DenyAssumeRoleNotResource",
        )

    @cached_property
    def statement_deny_cost_explorer(self) -> Statement:
        """Statement to deny access to Cost Explorer and other associated information."""
        return Statement(
            Action=[
                Action("account", "*"),
                Action("aws-portal", "*"),
                Action("ce", "*"),
                Action("cur", "*"),
                Action("savingsplans", "*"),
            ],
            Effect=Deny,
            Resource=["*"],
            Sid="DenyCostAndBilling",
        )

    @cached_property
    def statement_deny_create_without_boundary(self) -> Statement:
        """Statement to deny creation of role or user without approved boundary."""
        return Statement(
            Action=[awacs.iam.CreateRole, awacs.iam.CreateUser],
            Condition=Condition(
                StringNotEquals(
                    {"iam:PermissionsBoundary": self.approved_boundary_policies}
                )
            ),
            Effect=Deny,
            Resource=[
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/*"),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:user/*"),
            ],
            Sid="DenyCreateWithoutBoundary",
        )

    @cached_property
    def statement_deny_onica_sso(self) -> Statement:
        """IAM Policy to DENY access to Onica SSO resources."""
        return Statement(
            Action=[Action("*")],
            Effect=Deny,
            Resource=[
                Sub(
                    "arn:${AWS::Partition}:cloudformation:*:${AWS::AccountId}:stack/"
                    "onica-sso"
                ),
                Sub(
                    "arn:${AWS::Partition}:cloudformation:*:${AWS::AccountId}:stack/"
                    "onica-sso-*"
                ),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:policy/onica-sso"),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:policy/onica-sso-*"),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/onica-sso"),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/onica-sso-*"),
            ],
        )

    @cached_property
    def statement_deny_put_boundary(self) -> Statement:
        """Statement to deny putting unapproved boundaries."""
        return Statement(
            Action=[
                awacs.iam.PutRolePermissionsBoundary,
                awacs.iam.PutUserPermissionsBoundary,
            ],
            Condition=Condition(
                StringNotEquals(
                    {"iam:PermissionsBoundary": self.approved_boundary_policies}
                )
            ),
            Effect=Deny,
            Resource=[
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/*"),
                Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:user/*"),
            ],
            Sid="DenyPutUnapprovedBoundary",
        )

    @cached_property
    def statement_deny_remove_boundary_policy(self) -> Statement:
        """Statement to deny the removal of the boundary policy."""
        return Statement(
            Action=[
                awacs.iam.DeleteRolePermissionsBoundary,
                awacs.iam.DeleteUserPermissionsBoundary,
            ],
            Condition=Condition(
                StringEquals({"iam:PermissionsBoundary": self.policy_arn})
            ),
            Effect=Deny,
            Resource=["*"],
            Sid="DenyRemovalOfBoundaryFromUserOrRole",
        )

    @cached_property
    def statements(self) -> List[Statement]:
        """List of statements to add to the policy."""
        return [
            self.statement_allow_admin_access,
            self.statement_deny_alter_boundary_policy,
            self.statement_deny_assume_role_not_resource,
            self.statement_deny_cost_explorer,
            self.statement_deny_create_without_boundary,
            self.statement_deny_onica_sso,
            self.statement_deny_put_boundary,
            self.statement_deny_remove_boundary_policy,
        ]

    def create_template(self) -> None:
        """Create a template from the Blueprint."""
        self.template.set_description(self.DESCRIPTION)
        self.template.set_version("2010-09-09")

        policy = ManagedPolicy(
            "Policy",
            template=self.template,
            Description=self.DESCRIPTION,
            ManagedPolicyName=self.POLICY_NAME,
            PolicyDocument=PolicyDocument(
                Statement=self.statements,
                Version="2012-10-17",
            ),
        )
        self.add_output(policy.title, self.POLICY_NAME)
        self.add_output(f"{policy.title}Arn", policy.ref())
