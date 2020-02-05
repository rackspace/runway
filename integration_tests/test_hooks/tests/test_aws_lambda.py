"""Test AWS Lambda hook."""
import os
from integration_tests.test_hooks.test_hooks import Hooks
from integration_tests.util import run_command, copy_file
from runway.util import change_dir
import shutil
import boto3

class TestAwsLambda(Hooks):
    """Test AWS Lambda Hook from cfngin."""
    TEST_NAME = __name__
    TEMPLATES = ['dockerizepip.yml', 'nondockerizepip.yml']
    CLIENT = boto3.client('lambda', region_name='us-east-1')

    @property
    def lambda_dir(self):
        return os.path.join(self.tests_dir, 'aws_lambda')

    @property
    def template_dir(self):
        return os.path.join(self.lambda_dir, 'templates')

    def deploy_template(self, template, cmd='deploy'):
        """Copy template and deploy."""
        copy_file(os.path.join(self.template_dir, template), self.lambda_dir)
        with change_dir(self.lambda_dir):
            return run_command(['runway', 'deploy'])
    
    def invoke_lambda(self, func_name):
        """Verify lambda function deployed successfully."""
        self.logger.info('Invoking lambda function: %s', func_name)
        resp = self.CLIENT.invoke(
            FunctionName=func_name,
            InvocationType='RequestResponse'
        )

        return resp['StatusCode']

    def run(self):
        """Run test."""
        for template in self.TEMPLATES:
            assert self.deploy_template(template) == 0, \
                '{}: {} failed'.format(self.TEST_NAME, template)
            func_name = '%s-integrationtest' % template.split('.')[0]
            assert self.invoke_lambda(func_name) == 200, \
                '{}: Execution of lambda {} failed'.format(self.TEST_NAME, func_name)
            os.remove(os.path.join(self.lambda_dir, template))

    
    def teardown(self):
        """Teardown test."""
        for template in self.TEMPLATES:
            self.deploy_template(template, 'destroy')
