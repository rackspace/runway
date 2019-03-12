"""The init command."""
from __future__ import print_function

import os
import sys

from ..runway_command import RunwayCommand


class Init(RunwayCommand):
    """Extend Base with init command."""

    def execute(self):  # pylint: disable=no-self-use
        """Generate runway.yml."""
        if os.path.isfile('runway.yml'):
            print('Runway config already present')
            sys.exit(1)
        with open('runway.yml', 'w') as stream:
            stream.write("""---
deployments:
  - modules:
      - nameofmyfirstmodulefolder
      - nameofmysecondmodulefolder
      # - etc...
    regions:
      - us-east-1
""")
        print('runway.yml generated')
        print('See additional getting started information at '
              'https://docs.onica.com/projects/runway/en/latest/how_to_use.html')  # noqa pylint: disable=line-too-long
