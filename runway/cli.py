"""
Runway Overview.

Usage:
  runway (test|preflight)
  runway (plan|taxi)
  runway (deploy|takeoff)
  runway (destroy|dismantle)
  runway init
  runway gitclean
  runway gen-sample (cfn|sls-tsc|sls|tf|stacker|cdk-tsc|cdk-py|cdk-csharp)
  runway whichenv
  runway -h | --help
  runway --version

Options:
  -h --help                         Show this screen.
  --version                         Show version.

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

from docopt import docopt

from . import __version__ as version

from .commands.command_loader import find_command_class

LOGGER = logging.getLogger('runway')


def fix_hyphen_commands(raw_cli_arguments):
    """Update options to match their module names with underscores."""
    for i in ['gen-sample']:
        raw_cli_arguments[i.replace('-', '_')] = raw_cli_arguments[i]
        raw_cli_arguments.pop(i)
    return raw_cli_arguments


def main():
    """Provide main CLI entrypoint."""
    if os.environ.get('DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
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
