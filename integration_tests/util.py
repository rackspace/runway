"""Utility functions."""
import glob
import os
import importlib
import shutil
import subprocess
from prettytable import PrettyTable
from integration_tests.integration_test import IntegrationTest


def run_command(cmd_list, env_vars=None):
    """Shell out to provisioner command."""
    try:
        subprocess.check_call(cmd_list, env=env_vars)
    except subprocess.CalledProcessError as shelloutexc:
        return shelloutexc.returncode
    return 0


def import_tests(logger, path, pattern, use_abs=True):
    """Find and import all tests from a given path."""
    logger.info('Loading tests from "%s" with pattern: "%s"', path, pattern)
    tests = glob.glob(os.path.join(path, '{}.py'.format(pattern)))
    for test in tests:
        relpath = os.path.relpath(test)[:-3]
        test_name = relpath.replace(os.path.sep, '.')
        logger.info('Found test: "%s". Attempting to import...', test_name)
        if use_abs:
            final_path = os.path.abspath(relpath).split('/runway/')[1].replace('/', '.')
        else:
            final_path = relpath
        try:
            importlib.import_module(final_path)
        except ModuleNotFoundError as moderr:
            logger.info('Failed to import test: "%s". Error: "%s"', test_name, moderr)
            raise moderr


def execute_tests(tests, logger):
    """Run the given set of tests."""
    err_count = 0
    results = {}
    for test in tests:
        test_name = test.__class__.__name__

        if not issubclass(test.__class__, IntegrationTest):
            logger.error('%s does not inherit from "IntegrationTest", skipping...',
                         test_name)
            continue

        logger.info('==========================Executing test "%s"' +
                    '==========================', test_name)

        try:
            logger.info('Executing "run" for "%s"...', test_name)
            test.run()
            results[test_name] = 'Success'
        except AssertionError as assert_err:
            logger.error('AssertionError: "%s"', assert_err)
            err_count += 1
            results[test_name] = 'Failed'
        finally:
            try:
                logger.info('Executing "teardown" for "%s"...', test_name)
                test.teardown()
            except BaseException as err:
                logger.error("Teardown failed for test \"%s\". "
                             "Some resources may need to be cleaned up manually.",
                             test_name)
                logger.error(err)

    tbl = PrettyTable(['Test Name', 'Result'])
    tbl.align['Test Name'] = 'l'

    for key, value in results.items():
        tbl.add_row([key, value])

    logger.info('\r\n==========================Test Results==========================' +
                '\r\n' + str(tbl) + '\r\n%s out of %s Tests Passed',
                (len(tests) - err_count), len(tests))
    return err_count


def copy_file(src, dest):
    """Copy file to destination."""
    if os.path.isfile(src):
        shutil.copy(src, dest)
    else:
        print('copy: File not found: %s' % src)


def copy_dir(src, dest):
    """Copy dir to destination."""
    if os.path.isdir(src):
        shutil.copytree(src, dest, copy_function=shutil.copy2)
