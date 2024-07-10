"""Blueprint for a test runner user."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

import awacs.sts
from awacs.aws import Deny, PolicyDocument, Statement
from troposphere.iam import Policy

from .admin_user import AdminUser

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class TestRunnerUser(AdminUser):
    """Blueprint for a test runner user."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "DenyAssumeRoleNotResources": {"type": list, "default": []},
        "PermissionsBoundary": {"type": str},
        "UserName": {"type": str, "default": ""},
    }

    def create_template(self) -> None:
        """Create a template from the Blueprint."""
        self.template.set_description("Test runner user")
        self.template.set_version("2010-09-09")
        self.user.Policies = [
            Policy(
                PolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Action=[awacs.sts.AssumeRole],
                            Effect=Deny,
                            NotResource=self.variables["DenyAssumeRoleNotResources"] or ["*"],
                        )
                    ],
                    Version="2012-10-17",
                ),
                PolicyName="AssumeRolePolicy",
            )
        ]
