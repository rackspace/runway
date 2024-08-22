"""Blueprint for an admin user."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from troposphere import NoValue
from troposphere.iam import User

from runway.cfngin.blueprints.base import Blueprint
from runway.compat import cached_property

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class AdminUser(Blueprint):
    """Blueprint for an admin user."""

    VARIABLES: ClassVar[dict[str, BlueprintVariableTypeDef]] = {
        "PermissionsBoundary": {"type": str},
        "UserName": {"type": str, "default": ""},
    }

    @cached_property
    def namespace(self) -> str:
        """Stack namespace."""
        return self.context.namespace

    @cached_property
    def user(self) -> User:
        """User."""
        user = User(
            "User",
            template=self.template,
            ManagedPolicyArns=["arn:aws:iam::aws:policy/AdministratorAccess"],
            PermissionsBoundary=self.variables["PermissionsBoundary"],
            UserName=self.username or NoValue,
        )
        self.add_output(user.title, user.ref())
        self.add_output(f"{user.title}Arn", user.get_att("Arn"))
        return user

    @cached_property
    def username(self) -> str | None:
        """Name of the user being created."""
        val = self.variables["UserName"]
        if val == "":
            return None
        return val

    def create_template(self) -> None:
        """Create a template from the Blueprint."""
        self.template.set_description("Admin user")
        self.template.set_version("2010-09-09")
        self.user  # noqa: B018
