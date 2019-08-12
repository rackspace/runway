"""Utility functions."""
import glob
import os
import importlib
import shutil


def import_tests(path, pattern='test_*/test_*'):
    """Find and import all tests from a given path."""
    print('PATH: %s' % path)
    tests = glob.glob(os.path.join(path, '{}.py'.format(pattern)))
    for test in tests:
        relpath = os.path.relpath(test)[:-3]
        test_name = relpath.replace('\\', '.')
        print('Found test: %s. Attempting to import...' % test_name)
        try:
            importlib.import_module(test_name)
        except ModuleNotFoundError as moderr:
            print('Failed to import test: %s. %s' % test_name, moderr)


def execute_tests(self, tests):
    """Run the given set of tests."""
    err_count = 0
    for test in tests:
        itest = test(self)
        test_name = test.__name__
        self.LOGGER.info('Executing test "%s"...', test_name)

        try:
            self.LOGGER.info('Executing "init" for "%s"...', test_name)
            itest.init()
            self.LOGGER.info('Executing "run" for "%s"...', test_name)
            itest.run()
        except AssertionError as assert_err:
            self.LOGGER.error('AssertionError: "%s"', assert_err)
            err_count += 1
        finally:
            try:
                self.LOGGER.info('Executing "teardown" for "%s"...', test_name)
                itest.teardown()
            except BaseException as err:
                self.LOGGER.error("""Teardown failed for test "%s".
                                  Some resources may need to be cleaned up manually.""",
                                  test.__name__)
                self.LOGGER.error(err)

    return err_count


def copy_file(src, dest):
    """Copy file to destination."""
    if os.path.isfile(src):
        shutil.copy(src, dest)
    else:
        print('copy: File not found: %s' % src)
