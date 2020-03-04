"""Cloudformation module."""
import logging

from ..cfngin import CFNgin
from . import RunwayModule

LOGGER = logging.getLogger('runway')


class CloudFormation(RunwayModule):
    """CloudFormation (Stacker) Runway Module."""

    def deploy(self):
        """Run stacker build."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.deploy(force=self.options['environment'])

    def destroy(self):
        """Run stacker destroy."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.destroy(force=self.options['environment'])

    def plan(self):
        """Run stacker diff."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.plan(force=self.options['environment'])
