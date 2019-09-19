"""Re-usable class for Serverless testing."""
import os
from util import run_command
from runway.util import change_dir
from test_serverless.test_serverless import Serverless


class ServerlessTest(Serverless):
    """Class for Serverless tests."""

    ENVS = ('dev', 'test')

    def __init__(self, template, templates_dir, environment, logger):
        """Initialize class."""
        self.template_name = template
        self.templates_dir = templates_dir
        self.environment = environment
        self.logger = logger

    def run_runway(self, template, command='deploy'):
        """Deploy serverless template."""
        template_dir = os.path.join(self.templates_dir, template)
        if os.path.isdir(template_dir):
            self.logger.info('Executing test "%s" in directory "%s"', template, template_dir)
            with change_dir(template_dir):
                self.logger.info('Running "runway %s" on %s', command, template_dir)
                return run_command(['runway', command], self.environment)
        else:
            self.logger.error('Directory not found: %s', template_dir)
            return 1

    def init(self):
        """Run init."""

    def run(self):
        """Run tests."""
        print('what')
        for env in self.ENVS:
            self.set_environment(env)
            assert self.run_runway(self.template_name) == 0,\
                '{}: Failed to deploy in {} environment'.format(self.template_name, env)

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info('Tearing down: %s', self.template_name)
        for env in self.ENVS:
            self.set_environment(env)
            self.run_runway(self.template_name, 'destroy')
