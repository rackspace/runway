"""Integration test module."""
import os
from copy import deepcopy
import yaml


class IntegrationTest(object):
    """Base class for Integration Tests."""

    WORKING_DIR = os.path.abspath(os.path.dirname(__file__))

    def __init__(self, logger):
        """Initialize base class."""
        self.logger = logger
        self.environment = deepcopy(os.environ)
        self.runway_config_path = None

    def parse_config(self, path):
        """Read and parse yml."""
        if not os.path.isfile(path):
            self.logger.error("Config file was not found (looking for \"%s\")",
                              path)
        with open(path) as data_file:
            return yaml.safe_load(data_file)

    def set_environment(self, env):
        """Set deploy environment."""
        self.logger.info('Setting "DEPLOY_ENVIRONMENT" to "%s"', env)
        if not isinstance(env, dict):
            env = {'DEPLOY_ENVIRONMENT': env}
        self.environment.update(env)

    def run(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the run() method '
                                  'yourself!')

    def teardown(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the teardown() method '
                                  'yourself!')
