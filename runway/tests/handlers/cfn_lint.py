"""cfn-list test runner."""
from __future__ import print_function

import logging
import os
import sys
from typing import Dict, Any  # pylint: disable=unused-import

import cfnlint.core

from runway.tests.handlers.base import TestHandler

TYPE_NAME = 'cfn-lint'
LOGGER = logging.getLogger('runway')


class CfnLintHandler(TestHandler):
    """Lints CFN."""

    @staticmethod
    def run_cfnlint(cli_args):
        # type: (str) -> int
        """Modify cfnlint.__main__.main to work here.

        https://github.com/aws-cloudformation/cfn-python-lint

        Args:
            cli_args: A string of comand line args as defined by cfn-lint.

        Returns:
            An exit code.

        """
        try:
            (args, filenames, formatter) = cfnlint.core.get_args_filenames(cli_args)
            matches = []
            for filename in filenames:
                LOGGER.debug('Begin linting of file: %s', str(filename))
                (template, rules, template_matches) = cfnlint.core.get_template_rules(filename,
                                                                                      args)
                if not template_matches:
                    matches.extend(
                        # no-value issue is a py2 pylint false positive
                        cfnlint.core.run_cli(  # pylint: disable=no-value-for-parameter
                            filename, template, rules,
                            args.regions, args.override_spec))
                else:
                    matches.extend(template_matches)
                LOGGER.debug('Completed linting of file: %s', str(filename))

            matches_output = formatter.print_matches(matches)
            if matches_output:
                print(matches_output)
            return cfnlint.core.get_exit_code(matches)
        except cfnlint.core.CfnLintExitException as err:
            LOGGER.error(str(err))
            return err.exit_code

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Perform the actual test.

        Relies on .cfnlintrc file to be located beside the Runway config file.

        """
        cfnlintrc_path = os.path.join(os.getcwd(), '.cfnlintrc')

        if not os.path.isfile(cfnlintrc_path):
            LOGGER.error('File must exist to use this test: %s', cfnlintrc_path)
            sys.exit(1)

        exit_code = cls.run_cfnlint(args.get('cli_args', ''))

        if exit_code != 0:
            sys.exit(exit_code)
