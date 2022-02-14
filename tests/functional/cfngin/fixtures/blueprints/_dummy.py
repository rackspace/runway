"""Dummy Blueprints."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Dict

from troposphere import Ref
from troposphere.cloudformation import WaitCondition, WaitConditionHandle

from runway.cfngin.blueprints.base import Blueprint

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


class Dummy(Blueprint):
    """Dummy blueprint."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "StringVariable": {"type": str, "default": ""}
    }

    def create_template(self) -> None:
        """Create template."""
        self.template.add_resource(WaitConditionHandle("Dummy"))
        self.add_output("DummyId", "dummy-1234")
        self.add_output("Region", Ref("AWS::Region"))


class LongRunningDummy(Blueprint):
    """Meant to be an attempt to create a cheap, slow blueprint.

    Takes a little bit of time to create/rollback/destroy to avoid some of the
    race conditions we've seen in some of our functional tests.

    """

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "Count": {
            "type": int,
            "description": "The # of WaitConditionHandles to create.",
            "default": 1,
        },
        "BreakLast": {
            "type": bool,
            "description": "Whether or not to break the last WaitCondition "
            "by creating an invalid WaitConditionHandle.",
            "default": True,
        },
        "OutputValue": {
            "type": str,
            "description": "The value to put in an output to allow for updates.",
            "default": "DefaultOutput",
        },
    }

    def create_template(self) -> None:
        """Create template."""
        base_name = "Dummy"

        for i in range(self.variables["Count"]):
            name = f"{base_name}{i}"
            last_name = None
            if i:
                last_name = f"{base_name}{i - 1}"
            wch = WaitConditionHandle(name)
            if last_name is not None:
                wch.DependsOn = last_name
            self.template.add_resource(wch)

            if self.variables["BreakLast"] and i == self.variables["Count"] - 1:
                self.template.add_resource(
                    WaitCondition(
                        "BrokenWaitCondition",
                        Handle=wch.Ref(),
                        # Timeout is made deliberately large so CF rejects it
                        Timeout=2**32,
                        Count=0,
                    )
                )

        self.add_output("OutputValue", str(self.variables["OutputValue"]))
        self.add_output("WCHCount", str(self.variables["Count"]))


class SecondDummy(Dummy):
    """Second dummy blueprint."""

    def create_template(self) -> None:
        """Create template."""
        self.template.add_resource(WaitConditionHandle("Dummy"))
        self.template.add_resource(WaitConditionHandle("SecondDummy"))
        self.add_output("DummyId", "dummy-1234")
