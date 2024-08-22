"""Blueprint for an admin role."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import awacs.sts
from awacs.aws import Allow, AWSPrincipal, PolicyDocument, Statement
from troposphere import NoValue
from troposphere.iam import Role

from runway.cfngin.blueprints.base import Blueprint
from runway.compat import cached_property

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class AdminRole(Blueprint):
    """Blueprint for an admin role."""

    VARIABLES: ClassVar[dict[str, BlueprintVariableTypeDef]] = {
        "CrossAccountAccessAccountIds": {"type": list, "default": []},
        "PermissionsBoundary": {"type": str},
        "RoleName": {"type": str, "default": ""},
    }

    @cached_property
    def assume_role_policy(self) -> PolicyDocument:
        """Assume role policy document."""
        policy_doc = PolicyDocument(Statement=[], Version="2012-10-17")
        if self.variables.get("CrossAccountAccessAccountIds"):
            policy_doc.Statement.append(
                Statement(
                    Action=[awacs.sts.AssumeRole],
                    Effect=Allow,
                    Principal=AWSPrincipal(self.variables["CrossAccountAccessAccountIds"]),
                )
            )
        return policy_doc

    @cached_property
    def namespace(self) -> str:
        """Stack namespace."""
        return self.context.namespace

    @cached_property
    def role_name(self) -> str | None:
        """Name of the role being created."""
        val = self.variables["RoleName"]
        if val == "":
            return None
        return val

    def create_template(self) -> None:
        """Create a template from the Blueprint."""
        self.template.set_description("Admin role")
        self.template.set_version("2010-09-09")

        role = Role(
            "Role",
            template=self.template,
            AssumeRolePolicyDocument=self.assume_role_policy,
            Description="Admin role",
            ManagedPolicyArns=["arn:aws:iam::aws:policy/AdministratorAccess"],
            MaxSessionDuration=3600,  # 1 hour
            PermissionsBoundary=self.variables["PermissionsBoundary"],
            RoleName=self.role_name or NoValue,
        )
        self.add_output(role.title, role.ref())
        self.add_output(f"{role.title}Arn", role.get_att("Arn"))
