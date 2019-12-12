"""Test helm provider."""
import os
from runway.util import change_dir
from test_helm.test_helm import Helm
from util import (run_command)


class ProviderTest(Helm):
    """Test helm deployment."""

    TEST_NAME = __name__

    def __init__(self, logger):
        """Init class."""
        self.logger = logger

    def deploy(self):
        """Deploy provider."""
        template_dir = os.path.join(self.template_dir, "helloworld")
        with change_dir(template_dir):
            return run_command(['runway', 'deploy', '--tag', 'app:runway-helm-test'])

    def destroy(self):
        """Deploy provider."""
        template_dir = os.path.join(self.template_dir, "helloworld")
        with change_dir(template_dir):
            return run_command(['runway', 'destroy', '--tag', 'app:runway-helm-test'])

    def run(self):
        """Run tests."""
        self.logger.info('Running: %s', self.TEST_NAME)
        response = self.deploy()
        assert response == 0, '{}: Helm deployment failed'.format(__name__)
        self.logger.info('Helm module successfully deployed: %s', self.TEST_NAME)

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        response = self.destroy()
        assert response == 0, '{}: Helm detroy failed'.format(__name__)
        self.logger.info('Helm module successfully destroyed: %s', self.TEST_NAME)
