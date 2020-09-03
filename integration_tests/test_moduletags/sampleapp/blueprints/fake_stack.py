"""Fake resource."""
from troposphere import cloudformation as cfn


from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNString


class BlueprintClass(Blueprint):  # pylint: disable=too-few-public-methods
    """Extends Blueprint."""

    VARIABLES = {"TestVar": {"type": CFNString, "default": ""}}

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        template.add_version("2010-09-09")
        template.add_description("just a template")

        template.add_resource(cfn.WaitConditionHandle("FakeResource"))
