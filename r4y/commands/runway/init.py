"""Creates a sample :ref:`r4y-config` in the current directory.

If a :ref:`Runway config file<r4y-config>` is already present, no
action is taken.

Example:
  .. code-block:: shell

    $ r4y init

.. rubric:: Sample Runway Config File
.. code-block:: yaml

    ---
    # See full syntax at https://docs.onica.com/projects/r4y/en/latest/
    deployments:
      - modules:
          - nameofmyfirstmodulefolder
          - nameofmysecondmodulefolder
          # - etc...
        regions:
          - us-east-1

"""
from __future__ import print_function

import os
import sys

from ..r4y_command import RunwayCommand


class Init(RunwayCommand):
    """Extend Base with init command."""

    SKIP_FIND_CONFIG = True

    def execute(self):  # pylint: disable=no-self-use
        """Generate r4y.yml."""
        if os.path.isfile('r4y.yml'):
            print('Runway config already present')
            sys.exit(1)
        with open('r4y.yml', 'w') as stream:
            stream.write("""---
# See full syntax at https://docs.onica.com/projects/r4y/en/latest/
deployments:
  - modules:
      - nameofmyfirstmodulefolder
      - nameofmysecondmodulefolder
      # - etc...
    regions:
      - us-east-1
""")
        print('r4y.yml generated')
        print('See additional getting started information at '
              'https://docs.onica.com/projects/r4y/en/latest/how_to_use.html')  # noqa pylint: disable=line-too-long
