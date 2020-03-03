"""Cloudformation module."""
import logging
import sys

import yaml

from . import RunwayModule
from ..cfngin import CFNgin

LOGGER = logging.getLogger('runway')


def ensure_stacker_compat_config(config_filename):
    """Ensure config file can be loaded by Stacker."""
    try:
        with open(config_filename, 'r') as stream:
            yaml.safe_load(stream)
    except yaml.constructor.ConstructorError as yaml_error:
        if yaml_error.problem.startswith(
                'could not determine a constructor for the tag \'!'):
            LOGGER.error('"%s" appears to be a CloudFormation template, '
                         'but is located in the top level of a module '
                         'alongside the CloudFormation config files (i.e. '
                         'the file or files indicating the stack names & '
                         'parameters). Please move the template to a '
                         'subdirectory.',
                         config_filename)
            sys.exit(1)


class CloudFormation(RunwayModule):
    """CloudFormation (Stacker) Runway Module."""

    def deploy(self):
        """Run stacker build."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.deploy()

    def destroy(self):
        """Run stacker destroy."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.destroy()

    def plan(self):
        """Run stacker diff."""
        cfngin = CFNgin(self.context,
                        parameters=self.options['parameters'],
                        sys_path=self.path)
        cfngin.plan()
