"""Broken Blueprints."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

from troposphere import Ref
from troposphere.cloudformation import WaitCondition, WaitConditionHandle

from runway.cfngin.blueprints.base import Blueprint

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class Broken(Blueprint):
    """Blueprint that deliberately fails validation.

    It can be used to test re-creation of a failed stack.

    """

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "StringVariable": {"type": str, "default": ""}
    }

    def create_template(self) -> None:
        """Create template."""
        self.template.add_resource(WaitConditionHandle("BrokenDummy"))
        self.template.add_resource(
            WaitCondition(
                "BrokenWaitCondition",
                Handle=Ref("BrokenDummy"),
                # Timeout is made deliberately large so CF rejects it
                Timeout=2**32,
                Count=0,
            )
        )
        self.add_output("DummyId", "dummy-1234")
