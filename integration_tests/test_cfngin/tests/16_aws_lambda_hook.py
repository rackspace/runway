"""Test AWS Lambda hook."""
# flake8: noqa
# pylint: disable=invalid-name
import os

import boto3
from click.testing import CliRunner
from send2trash import send2trash

from integration_tests.test_cfngin.test_cfngin import Cfngin
from runway._cli import cli
from runway.util import change_dir

FILE_BASENAME = ".".join(os.path.basename(__file__).split(".")[:-1])


class TestAwsLambda(Cfngin):
    """Test AWS Lambda Hook from cfngin.

    Requires valid AWS Credentials.

    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + ".yaml"]
    TEST_NAME = __name__

    def invoke_lambda(self, client, func_name):
        """Verify lambda function deployed successfully."""
        self.logger.info("Invoking lambda function: %s", func_name)
        resp = client.invoke(FunctionName=func_name, InvocationType="RequestResponse")

        return resp["StatusCode"]

    def _build(self):
        """Execute and assert initial build.

        Explicitly spawning with a tty here to ensure output
        (e.g. from pip) includes color

        """
        with change_dir(self.working_dir):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["deploy", "--deploy-environment", "dev", "--ci"], color=True
            )
            assert result.exit_code == 0, "exit code should be zero"
            assert (
                "\x1b[31mERROR: " not in result.output
            ), "no red ERROR should be present"

    def run(self):
        """Run test."""
        self.copy_fixtures()
        self._build()

        client = boto3.client("lambda", region_name=self.region)

        functions = [
            "dockerizepip-integrationtest",
            "nondockerizepip-integrationtest",
            "authatedge-integrationtest",
        ]
        for func_name in functions:
            assert (
                self.invoke_lambda(client, func_name) == 200
            ), f"{self.TEST_NAME}: Execution of lambda {func_name} failed"

    def teardown(self):
        """Teardown test."""
        self.runway_cmd("destroy")
        venv_dir = os.path.join(self.fixture_dir, "lambda_src/dockerize_src/.venv")
        if os.path.isdir(venv_dir):
            send2trash(venv_dir)
        self.cleanup_fixtures()
