"""
Runway Overview.

Usage:
  runway (test|preflight)
  runway (plan|taxi) [--tag <tag>...]
  runway (deploy|takeoff) [--tag <tag>...]
  runway (destroy|dismantle) [--tag <tag>...]
  runway init
  runway gen-sample [<samplename>]
  runway whichenv
  runway envvars
  runway run-aws <awscli-args>...
  runway run-python <filename>
  runway run-stacker <stacker-args>...
  runway tfenv (install|run) [<tfenv-args>...]
  runway kbenv (install|run) [<kbenv-args>...]
  runway -h | --help
  runway --version

Options:
  -h --help                         Show this screen.
  --version                         Show version.
  --tag <tag>...                    Select modules for processing by tag
                                    or tags. This option can be specified
                                    more than once to build a list of tags
                                    that are treated as "AND". (ex.
                                    "--tag <tag1> --tag <tag2>" would select
                                    all modules with BOTH tags).

Example:
  runway deploy --tag app:some-app --tag tier:web  # app:some-app AND tier:web
  runway destroy --tag app:some-app --tag tier:web  # app:some-app AND tier:web

Help:
  * Set the DEPLOY_ENVIRONMENT environment variable to set/override the
    autodetected environment. Autodetection is done from git branches in the
    form of ENV- (e.g. the dev environment is deployed from ENV-dev branch)
    falling back to name of the parent folder of the module.
  * All deploy commands (e.g. sls deploy, tf apply) will be run interactively
    unless the CI environment variable is set.

"""

import logging
import os
import sys

from docopt import docopt

from . import __version__ as version
from .cfngin.logger import ColorFormatter
from .commands.command_loader import find_command_class

# replicate stacker's colorized logs until we implement something better
COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')
HDLR = logging.StreamHandler()
HDLR.setFormatter(ColorFormatter(
    COLOR_FORMAT if sys.stdout.isatty() else logging.BASIC_FORMAT
))


def fix_hyphen_commands(raw_cli_arguments):
    """Update options to match their module names with underscores."""
    for i in ['gen-sample', 'run-aws', 'run-python', 'run-stacker']:
        raw_cli_arguments[i.replace('-', '_')] = raw_cli_arguments[i]
        raw_cli_arguments.pop(i)
    return raw_cli_arguments


def main():
    """Provide main CLI entrypoint."""
    if os.environ.get('DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO,
                            handlers=[HDLR])
        # botocore info is spammy
        logging.getLogger('botocore').setLevel(logging.ERROR)

    cli_arguments = fix_hyphen_commands(docopt(__doc__, version=version))

    # at least one of these must be enabled, i.e. the value is 'True'... but unfortunately
    #  `docopts` doesn't give you the hierarchy... so given 'gen-sample cfn', there are
    #  TWO enabled items in the list, 'gen-sample' and 'cfn'
    possible_commands = [command for command, enabled in cli_arguments.items() if enabled]

    command_class = find_command_class(possible_commands)
    if command_class:
        command_class(cli_arguments).execute()
    else:
        LOGGER.error("class not found for command '%s'", possible_commands)
