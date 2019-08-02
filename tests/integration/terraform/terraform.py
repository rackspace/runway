"""Integration tests for Terraform."""

import os
import shutil
import logging
import subprocess
from send2trash import send2trash
from runway.util import change_dir

WORKING_DIR = os.getcwd()
TERRAFORM_TF_DIR = os.path.join(WORKING_DIR, 'test_terraform.tf')
TERRAFORM_TESTS_DIR = os.path.join(WORKING_DIR, 'tests')
TERRAFORM_STATE_DIR = os.path.join(WORKING_DIR, 'tf_state.cfn')

LOGGER = logging.getLogger(__name__)
STACKER_COMMANDS = ['build', 'destroy']


def clean():
    """Clean Terraform directories and any main.tf created."""
    files_to_delete = ['main.tf', 'terraform.tfstate']
    dirs_to_delete = ['.terraform', 'terraform.tfstate.d']

    LOGGER.info('Running "runway destroy" ...')
    with change_dir(WORKING_DIR):
        subprocess.check_call('runway destroy', shell=True)

    for file_to_delete in files_to_delete:
        if os.path.isfile(os.path.join(TERRAFORM_TF_DIR, file_to_delete)):
            LOGGER.debug('Trashing %s', file_to_delete)
            send2trash(os.path.join(TERRAFORM_TF_DIR, file_to_delete))
    for dir_to_delete in dirs_to_delete:
        if os.path.isdir(os.path.join(TERRAFORM_TF_DIR, dir_to_delete)):
            LOGGER.debug('Trashing %s', dir_to_delete)
            send2trash(os.path.join(TERRAFORM_TF_DIR, dir_to_delete))


def run_test(test_name):
    """Rename test_name to main.tf and run runway."""
    if not test_name.endswith('.test'):
        test_name += '.test'

    if os.path.isfile(os.path.join(TERRAFORM_TESTS_DIR, test_name)):
        LOGGER.debug('Copying Terraform test: "%s" to main.tf', test_name)
        shutil.copy(os.path.join(TERRAFORM_TESTS_DIR, test_name),
                    os.path.join(TERRAFORM_TF_DIR, 'main.tf'))

        LOGGER.info('Running test "%s"', test_name)
        with change_dir(WORKING_DIR):
            try:
                subprocess.check_call(['runway', 'deploy'])
            except subprocess.CalledProcessError:
                # We don't want to stop the other tests.
                # Just return an error code of 1
                return 1
    else:
        LOGGER.warning('Test not found "%s"; skipping...', test_name)
        return 0


def run_stacker(command='build'):
    """Deploys the CFN module to create S3 and DynamoDB resources."""
    if command not in STACKER_COMMANDS:
        raise ValueError('run_stacker: command must be one of %s' % STACKER_COMMANDS)

    LOGGER.info('Running "%s" on tf_state.cfn ...', command)
    with change_dir(os.path.join(WORKING_DIR, TERRAFORM_STATE_DIR)):
        subprocess.check_call('stacker {} -i -r us-east-1 {} dev-us-east-1.env tfstate.yaml'
                              .format(command, '-f' if command == 'destroy' else ''),
                              shell=True)


def teardown():
    """Teardown all resources."""
    # terraform destory
    # stacker destory
    clean()
    run_stacker('destroy')


def run_tests():
    """Run all tests."""
    try:
        # --- Test Backend Change Local -> S3 ---
        results = [run_test('no-backend.tf'), run_test('s3-backend.tf')]
        if 1 in results:
            LOGGER.error('TEST FAILED: Local to S3 Backend')
        # ---------------------------------------

        # cleanup between tests
        clean()

        # --- Test Provider Version Change ---
        results = [run_test('provider-version1.tf'), run_test('provider-version2.tf')]
        if 1 in results:
            LOGGER.error('TEST FAILED: Provider Version Change')
        # ------------------------------------

        # --- Test Backend Change Local -> Local ---
        # This test will always fail because of how Terraform handles
        # changing from no backend (local) to a local backend with a path
        # specified. No matter what path you set, it won't copy the configuration
        # to the correct new local backend file.
        # results = [run_test('no-backend.tf'), run_test('local-backend.tf')]
        # if 1 in results:
        #     LOGGER.error('TEST FAILED: Local to Local Backend')
        # ------------------------------------------      
    except:  # noqa: E722 pylint: disable=bare-except
        LOGGER.error('TESTS FAILED, CHECK LOG')
    finally:
        teardown()


if __name__ == "__main__":
    run_stacker()
    run_tests()
