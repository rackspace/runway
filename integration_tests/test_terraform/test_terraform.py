"""Tests for Terraform."""
from __future__ import print_function
import os
import glob
import platform
from send2trash import send2trash
from runway.util import change_dir

from ..integration_test import IntegrationTest
from ..util import (copy_file, import_tests, execute_tests, run_command)


class Terraform(IntegrationTest):
    """Base class for all Terraform testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    tests_dir = os.path.join(base_dir, 'tests')

    tf_test_dir = os.path.join(base_dir, 'terraform_test.tf')
    tf_state_dir = os.path.join(base_dir, 'tf_state.cfn')

    def __init__(self, logger):
        IntegrationTest.__init__(self, logger)

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(self.template_dir, 'runway-{}.yml'.format(template))
        copy_file(template_file, os.path.join(self.base_dir, 'runway.yml'))

    def copy_template(self, template, name='main.tf'):
        """Copy template to Terraform module folder."""
        template_file = os.path.join(self.template_dir, template)
        copy_file(template_file, os.path.join(self.tf_test_dir, name))

    def clean(self):
        """Clean up Terraform module directory."""
        file_types = ('*.tf', '.terraform-version', '*.yaml', '*.yml', 'local_backend')
        templates = []
        for file_type in file_types:
            templates.extend(glob.glob(os.path.join(self.tf_test_dir, file_type)))
            templates.extend(glob.glob(os.path.join(self.base_dir, file_type)))

        for template in templates:
            if os.path.isfile(template):
                self.logger.debug('send2trash: "%s"', template)
                send2trash(template)
        folders = ('.terraform', 'terraform.tfstate.d')
        for folder in folders:
            folder_path = os.path.join(self.tf_test_dir, folder)
            if os.path.isdir(folder_path):
                self.logger.debug('send2trash: "%s"', folder_path)
                send2trash(folder_path)

        # destroy stacker tf-state
        self.run_stacker('destroy')

    def set_tf_version(self, version=11):
        """Copy version file to module directory."""
        version_file = 'tf-v{}.version'.format(version)
        self.copy_template(version_file, '.terraform-version')

    def run_stacker(self, command='build'):
        """Deploys the CFN module to create S3 and DynamoDB resources."""
        if command not in ('build', 'destroy'):
            raise ValueError('run_stacker: command must be one of %s' % ['build', 'destroy'])

        self.logger.info('Running "%s" on tf_state.cfn ...', command)
        self.logger.debug('tf_state_dir: %s', self.tf_state_dir)
        with change_dir(self.tf_state_dir):
            stacker_cmd = ['stacker.cmd' if platform.system().lower() == 'windows' else 'stacker',
                           command, '-i', '-r', 'us-east-1']
            if command == 'destroy':
                stacker_cmd = stacker_cmd + ['-f']
            stacker_cmd = stacker_cmd + ['dev-us-east-1.env', 'tfstate.yaml']
            self.logger.debug('STACKER_CMD: %s', stacker_cmd)
            cmd_opts = {'cmd_list': stacker_cmd}
            return run_command(**cmd_opts) # noqa

    def run(self):
        """Find all Terraform tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in Terraform.__subclasses__()]
        self.logger.debug('FOUND TESTS: %s', tests)
        self.set_environment('dev')
        return execute_tests(tests, self.logger)

    def teardown(self):
        """Teardown resources create during init."""
        self.clean()
