"""``runway test`` command."""
import logging
import traceback

import click

from ...context import Context
from ...tests.registry import TEST_HANDLERS
from .. import options

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('test', short_help='run tests')
@options.debug
@options.deploy_environment
@click.pass_context
def test(ctx, **_):
    """Execute tests as defined in the Runway config."""
    test_definitions = ctx.obj.runway_config.tests

    if not test_definitions:
        LOGGER.error(
            'Use of "runway test" without defining tests in the runway config '
            'file has been removed. See '
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
            click.secho(i, bold=True, err=True)
        ctx.exit(1)

    context = Context(command='test', deploy_environment=ctx.obj.env)

    failed_tests = []

    LOGGER.info('Found %i test(s)', len(test_definitions))
    for tst in test_definitions:
        tst.resolve(context, ctx.obj.runway_config.variables)
        LOGGER.info("")
        LOGGER.info("")
        LOGGER.info("======= Running test '%s' ===========================",
                    tst.name)
        try:
            handler = TEST_HANDLERS[tst.type]
        except KeyError:
            LOGGER.error('Unable to find handler for test %s of '
                         'type %s', tst.name, tst.type)
            if tst.required:
                ctx.exit(1)
            failed_tests.append(tst.name)
            continue
        try:
            handler.handle(tst.name, tst.args)
        except (Exception, SystemExit) as err:  # pylint: disable=broad-except
            # for lack of an easy, better way to do this atm, assume
            # SystemExits are due to a test failure and the failure reason
            # has already been properly logged by the handler or the
            # tool it is wrapping.
            if not isinstance(err, SystemExit):
                traceback.print_exc()
            LOGGER.error('Test failed: %s', tst.name)
            if tst.required:
                LOGGER.error('Failed test was required, the remaining '
                             'tests have been skipped')
                ctx.exit(1)
            failed_tests.append(tst.name)
    if failed_tests:
        LOGGER.error('The following tests failed: %s',
                     ', '.join(failed_tests))
        ctx.exit(1)
