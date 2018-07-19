"""
Runway Overview.

Usage:
  runway (test|preflight)
  runway (plan|taxi)
  runway (deploy|takeoff)
  runway (destroy|dismantle)
  runway gitclean
  runway gen-sample (cfn|sls|stacker|tf)
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


from inspect import getmembers, isclass
import logging
import os

from docopt import docopt

from . import __version__ as version


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

    from . import commands
    options = fix_hyphen_commands(docopt(__doc__, version=version))

    # Here we'll try to dynamically match the command the user is trying to run
    # with a pre-defined command class we've already created.
    for (key, val) in options.items():
        if hasattr(commands, key) and val:
            module = getattr(commands, key)
            commands = getmembers(module, isclass)
            command = [command[1] for command in commands if command[0] not in ['Base', 'Env', 'Module']][0]  # noqa pylint: disable=line-too-long
            command = command(options)
            command.execute()
