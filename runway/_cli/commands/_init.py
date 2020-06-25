"""Creates a sample :ref:`runway-config` in the current directory."""
import logging
import sys

import click
import six

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace('._', '.'))
RUNWAY_YML = """---
# See full syntax at https://docs.onica.com/projects/runway/en/latest/
deployments:
  - modules:
      - path: sampleapp.cfn
      - path: sampleapp.tf
      # - etc...
    regions:
      - us-east-1
"""


@click.command('init', short_help='create runway.yml')
@click.pass_context
def init(ctx):
    # type: (click.Context) -> None
    """Create an example runway.yml file in the currect directory."""
    runway_yml = Path.cwd() / 'runway.yml'

    if runway_yml.is_file():
        LOGGER.error('There is already a %s file in the current directory',
                     runway_yml.name)
        ctx.exit(1)

    # TODO remove use of six when dropping python 2
    runway_yml.write_text(six.u(RUNWAY_YML))
    LOGGER.info('runway.yml generated')
    LOGGER.info(
        'See addition getting started information at '
        'https://docs.onica.com/projects/runway/en/latest/getting_started.html'
    )
