"""Execute :ref:`tests<runway-test>` as defined in the :ref:`runway-config`.

If one of the tests fails, the command will exit unless the ``required``
option is set to ``false`` for the failing test. If it is not required,
the next test will be executed.

References:
    - :ref:`Runway Config File/Test<runway-test>`
    - :ref:`Defining Tests<defining-tests>`

"""
from __future__ import print_function
import logging
import os
import sys
import traceback

from ..base_command import BaseCommand
from ...context import Context
from ...tests.registry import TEST_HANDLERS

LOGGER = logging.getLogger('runway')


class Test(BaseCommand):  # pylint: disable=too-few-public-methods
    """Execute the test blocks of a runway config."""

    def execute(self):
        """Execute the test blocks of a runway config."""
        test_definitions = self.runway_config.tests

        if not test_definitions:
            LOGGER.error('Use of "runway test" without defining '
                         'tests in the runway config file has been '
                         'removed. See '
                         'https://docs.onica.com/projects/runway/en/release/defining_tests.html')
            LOGGER.error('E.g.:')
            for i in ['tests:',
                      '  - name: example-test',
                      '    type: script',
                      '    required: true',
                      '    args:',
                      '      commands:',
                      '        - echo "Success!"',
                      '']:
                print(i, file=sys.stderr)
            sys.exit(1)

        context = Context(env_name=os.getenv('DEPLOY_ENVIRONMENT', 'test'),
                          env_region=None,
                          env_root=self.env_root,
                          env_vars=os.environ.copy(),
                          command='test')

        LOGGER.info('Found %i test(s)', len(test_definitions))
        for test in test_definitions:
            test.resolve(context, self.runway_vars)
            LOGGER.info("")
            LOGGER.info("")
            LOGGER.info("======= Running test '%s' ===========================",
                        test.name)
            try:
                handler = TEST_HANDLERS[test.type]
            except KeyError:
                LOGGER.error('Unable to find handler for test %s of '
                             'type %s', test.name, test.type)
                if test.required:
                    sys.exit(1)
                continue
            try:
                handler.handle(test.name, test.args)
            except (Exception, SystemExit) as err:  # pylint: disable=broad-except
                # for lack of an easy, better way to do this atm, assume
                # SystemExits are due to a test failure and the failure reason
                # has already been properly logged by the handler or the
                # tool it is wrapping.
                if not isinstance(err, SystemExit):
                    traceback.print_exc()
                LOGGER.error('Test failed: %s', test.name)
                if test.required:
                    sys.exit(1)
