"""Testing that when CI is not set it still will launch the regions in series."""
from integration_tests.test_parallelism.test_parallelism import Parallelism
from integration_tests.util import run_command
from runway.util import change_dir


class TestDefaultToSeries(Parallelism):
    """Test deploying two regions in series."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture("sampleapp.cfn")
        self.copy_runway("default-to-series")
        with change_dir(self.parallelism_test_dir):
            return run_command(["runway", "deploy"])

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, "{}: Default to series failed".format(__name__)

    def teardown(self):
        """Teardown scaffolding."""
        self.set_env_var("CI", "1")
        self.logger.info("Tearing down: %s", self.TEST_NAME)
        with change_dir(self.parallelism_test_dir):
            run_command(["runway", "destroy"])
        self.clean()
