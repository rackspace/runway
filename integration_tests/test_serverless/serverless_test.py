"""Re-usable class for Serverless testing."""
import os
from util import run_command
from runway.util import change_dir
from test_serverless.test_serverless import Serverless


class ServerlessTest(Serverless):
    """Class for Serverless tests."""

    def __init__(self, template, templates_dir, logger):
        """Initialize class."""
        self.template_name = template
        self.templates_dir = templates_dir
        self.logger = logger

    def run_runway(self, template, command='deploy'):
        """Deploy serverless template."""
        template_dir = os.path.join(self.templates_dir, template)
        if os.path.isdir(template_dir):
            self.logger.info('Executing test "%s" in directory "%s"', template, template_dir)
            with change_dir(template_dir):
                return run_command(['runway', command])
        else:
            self.logger.error('Directory not found: %s', template_dir)
            return 1

    def init(self):
        """Run init."""

    def run(self):
        """Run tests."""
        assert self.run_runway(self.template_name) == 0,\
            '{}: Failed to deploy'.format(self.template_name)

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info('Tearing down: %s', self.template_name)
        self.run_runway(self.template_name, 'destroy')
