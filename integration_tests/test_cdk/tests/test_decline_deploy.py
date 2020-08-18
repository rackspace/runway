"""Test to verify behavior on declining deployment."""
import sys

import pexpect

from integration_tests.test_cdk.test_cdk import CDK
from runway.util import change_dir


class TestDeclineDeploy(CDK):
    """Test to verify behavior on declining deployment."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture("decline-deploy-app.cdk")
        self.copy_runway("decline-deploy")
        with change_dir(self.cdk_test_dir):
            child = pexpect.spawn("runway deploy")
            try:
                child.logfile = sys.stdout.buffer
                child.expect("Do you wish to deploy these changes (y/n)?", timeout=120)
                child.sendline("n")
                i = child.expect("Aborted")
            except pexpect.EOF:
                self.logger.debug("EOF Reached")
                return 0
            else:
                return i

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, "{}: Declining Deployment failed".format(__name__)

    def teardown(self):
        """Teardown."""
        self.logger.info("Tearing down: %s", self.TEST_NAME)
        self.clean()
