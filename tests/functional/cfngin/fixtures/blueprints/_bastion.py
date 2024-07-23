"""Bastion Blueprints."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import (
    CFNCommaDelimitedList,
    CFNNumber,
    CFNString,
    EC2KeyPairKeyName,
    EC2SecurityGroupId,
    EC2SubnetIdList,
    EC2VPCId,
)

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class FakeBastion(Blueprint):
    """Fake Bastion."""

    VARIABLES: ClassVar[dict[str, BlueprintVariableTypeDef]] = {
        "VpcId": {"type": EC2VPCId, "description": "Vpc Id"},
        "DefaultSG": {
            "type": EC2SecurityGroupId,
            "description": "Top level security group.",
        },
        "PublicSubnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets to deploy public instances in.",
        },
        "PrivateSubnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets to deploy private instances in.",
        },
        "AvailabilityZones": {
            "type": CFNCommaDelimitedList,
            "description": "Availability Zones to deploy instances in.",
        },
        "InstanceType": {
            "type": CFNString,
            "description": "EC2 Instance Type",
            "default": "m3.medium",
        },
        "MinSize": {
            "type": CFNNumber,
            "description": "Minimum # of instances.",
            "default": "1",
        },
        "MaxSize": {
            "type": CFNNumber,
            "description": "Maximum # of instances.",
            "default": "5",
        },
        "SshKeyName": {"type": EC2KeyPairKeyName},
        "OfficeNetwork": {
            "type": CFNString,
            "description": "CIDR block allowed to connect to bastion hosts.",
        },
        "ImageName": {
            "type": CFNString,
            "description": "The image name to use from the AMIMap (usually "
            "found in the config file.)",
            "default": "bastion",
        },
    }

    def create_template(self) -> None:
        """Create template."""
