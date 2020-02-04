"""Fake resource."""
from troposphere import cloudformation as cfn

# leave these as stacker
from stacker.blueprints.base import Blueprint  # noqa pylint: disable=import-error
from stacker.blueprints.variables.types import CFNString  # noqa pylint: disable=import-error


class BlueprintClass(Blueprint):
    """Extends Blueprint."""

    VARIABLES = {
        'TestVar': {
            'type': CFNString,
            'default': ''
        }
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        template.add_version('2010-09-09')
        template.add_description('just a template')

        template.add_resource(cfn.WaitConditionHandle('FakeResource'))
