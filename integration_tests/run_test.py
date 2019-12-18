"""Entrypoint for running tests."""
import sys
import os

# need to manipulate the path a bit since this exists inside the package
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(
    os.path.join(os.getcwd(), os.path.expanduser(__file__))
))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from integration_tests.runner import Runner  # noqa pylint: disable=wrong-import-position


if __name__ == "__main__":
    TEST_NAME = None
    if len(sys.argv) > 1:
        TEST_NAME = sys.argv[1]
    RUNNER = Runner(TEST_NAME, use_abs=True)
    sys.exit(RUNNER.main())
