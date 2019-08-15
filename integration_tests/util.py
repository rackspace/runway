"""Utility functions."""
import glob
import os
import importlib
import shutil
from prettytable import PrettyTable
from integration_test import IntegrationTest


def import_tests(self, path, pattern='test_*/test_*'):
    """Find and import all tests from a given path."""
    self.LOGGER.info('Loading tests from "%s" with pattern:', path)
    tests = glob.glob(os.path.join(path, '{}.py'.format(pattern)))
    for test in tests:
        relpath = os.path.relpath(test)[:-3]
        test_name = relpath.replace(os.path.sep, '.')
        self.LOGGER.info('Found test: "%s". Attempting to import...', test_name)
        try:
            importlib.import_module(test_name)
        except ModuleNotFoundError as moderr:
            self.LOGGER.info('Failed to import test: "%s". Error: "%s"', test_name, moderr)
            raise moderr


def execute_tests(self, tests):
    """Run the given set of tests."""
    err_count = 0
    results = {}
    for test in tests:
        itest = test(self)
        test_name = test.__name__

        if not issubclass(itest, IntegrationTest):
            self.LOGGER.error('%s does not inherit from "IntegrationTest", skipping...', test_name)
            continue

        self.LOGGER.info('==========================Executing test "%s"' +
                         '==========================', test_name)

        try:
            self.LOGGER.info('Executing "init" for "%s"...', test_name)
            itest.init()
            self.LOGGER.info('Executing "run" for "%s"...', test_name)
            itest.run()
            results[test_name] = 'Success'
        except AssertionError as assert_err:
            self.LOGGER.error('AssertionError: "%s"', assert_err)
            err_count += 1
            results[test_name] = 'Failed'
        finally:
            try:
                self.LOGGER.info('Executing "teardown" for "%s"...', test_name)
                itest.teardown()
            except BaseException as err:
                self.LOGGER.error("""Teardown failed for test "%s".
                                  Some resources may need to be cleaned up manually.""",
                                  test.__name__)
                self.LOGGER.error(err)

    tbl = PrettyTable(['Test Name', 'Result'])
    tbl.align['Test Name'] = 'l'

    for key, value in results.items():
        tbl.add_row([key, value])

    self.LOGGER.info('\r\n==========================Test Results==========================' +
                     '\r\n' + str(tbl) + '\r\n%s out of %s Tests Passed',
                     (len(tests) - err_count), len(tests))
    return err_count


def copy_file(src, dest):
    """Copy file to destination."""
    if os.path.isfile(src):
        shutil.copy(src, dest)
    else:
        print('copy: File not found: %s' % src)
