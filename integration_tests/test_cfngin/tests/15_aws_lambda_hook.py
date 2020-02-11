"""Test AWS Lambda hook."""
import os
from integration_tests.test_hooks.test_hooks import Hooks
from integration_tests.util import run_command, copy_file
from runway.util import change_dir
import shutil
import boto3

class TestAwsLambda(Hooks):
    """Test AWS Lambda Hook from cfngin.
    
    Requires valid AWS Credentials.
    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + '.yaml']
    TEST_NAME = __name__

    CLIENT = boto3.client('lambda', region_name='us-east-1')
    
    def invoke_lambda(self, func_name):
        """Verify lambda function deployed successfully."""
        self.logger.info('Invoking lambda function: %s', func_name)
        resp = self.CLIENT.invoke(
            FunctionName=func_name,
            InvocationType='RequestResponse'
        )

        return resp['StatusCode']

    def _build(self):
        """Execute and assert initial build."""
        self.set_environment('dev')
        code, _stdout, _stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'

    def run(self):
        """Run test."""
        self.copy_fixtures()
        self._build()

        funcs = ['dockerizepip-integrationtest',
                 'nondockerizepip-integrationtest']
        for func in funcs:
            assert self.invoke_lambda(func_name) == 200, \
                '{}: Execution of lambda {} failed'.format(self.TEST_NAME, func_name)
    
    def teardown(self):
        """Teardown test."""
        self.runway_cmd('destroy')
        self.cleanup_fixtures()

