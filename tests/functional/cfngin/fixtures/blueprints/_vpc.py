"""VPC Blueprints."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from troposphere.cloudformation import WaitConditionHandle

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNCommaDelimitedList, CFNString

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class FakeVPC(Blueprint):
    """Fake VPC."""

    VARIABLES: ClassVar[dict[str, BlueprintVariableTypeDef]] = {
        "AZCount": {"type": int, "default": 2},
        "PrivateSubnets": {
            "type": CFNCommaDelimitedList,
            "description": "Comma separated list of subnets to use for "
            "non-public hosts. NOTE: Must have as many subnets "
            "as AZCount",
        },
        "PublicSubnets": {
            "type": CFNCommaDelimitedList,
            "description": "Comma separated list of subnets to use for "
            "public hosts. NOTE: Must have as many subnets "
            "as AZCount",
        },
        "InstanceType": {
            "type": CFNString,
            "description": "NAT EC2 instance type.",
            "default": "m3.medium",
        },
        "BaseDomain": {
            "type": CFNString,
            "default": "",
            "description": "Base domain for the stack.",
        },
        "InternalDomain": {
            "type": CFNString,
            "default": "",
            "description": "Internal domain name, if you have one.",
        },
        "CidrBlock": {
            "type": CFNString,
            "description": "Base CIDR block for subnets.",
            "default": "10.128.0.0/16",
        },
        "ImageName": {
            "type": CFNString,
            "description": "The image name to use from the AMIMap (usually "
            "found in the config file.)",
            "default": "NAT",
        },
        "UseNatGateway": {
            "type": CFNString,
            "allowed_values": ["true", "false"],
            "description": "If set to true, will configure a NAT Gateway"
            "instead of NAT instances.",
            "default": "false",
        },
    }

    def create_template(self) -> None:
        """Create template."""
        self.template.add_resource(WaitConditionHandle("VPC"))
