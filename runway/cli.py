"""
Runway Overview.

Usage:
  runway (test|preflight)
  runway (plan|taxi)
  runway (deploy|takeoff)
  runway (destroy|dismantle)
  runway init
  runway gitclean
  runway gen-sample (cfn|sls-tsc|tf|stacker|cdk|sls)
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


def fix_hyphen_commands(raw_options):
    """Update options to match their module names with underscores."""
    for i in ['gen-sample']:
        raw_options[i.replace('-', '_')] = raw_options[i]
        raw_options.pop(i)
    return raw_options


def main():
    """Provide main CLI entrypoint."""
    if os.environ.get('DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        # botocore info is spammy
        logging.getLogger('botocore').setLevel(logging.ERROR)

    options = fix_hyphen_commands(docopt(__doc__, version=version))

    # at least one of these must be 'True'
    command_name = [command for command, enabled in options.items() if enabled][0]

    command_class = find_command_class(command_name)
    if command_class:
        command_class(options).execute()
    else:
        LOGGER.error("class not found for command '%s'", command_name)
