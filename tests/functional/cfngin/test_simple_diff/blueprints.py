"""Blueprint."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

from troposphere.cloudformation import WaitConditionHandle

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class DiffTester(Blueprint):
    """Diff tester."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "InstanceType": {
            "type": CFNString,
            "description": "NAT EC2 instance type.",
            "default": "m3.medium",
        },
        "WaitConditionCount": {
            "type": int,
            "description": "Number of WaitConditionHandle resources " "to add to the template",
        },
    }

    def create_template(self) -> None:
        """Create template."""
        for i in range(self.variables["WaitConditionCount"]):
            self.template.add_resource(WaitConditionHandle(f"VPC{i}"))
