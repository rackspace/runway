"""Integration test module."""
import subprocess
import logging
import os


class IntegrationTest(object):
    """Base class for Integration Tests."""

    WORKING_DIR = os.path.abspath(os.path.dirname(__file__))
    LOGGER = logging.getLogger('testsuite')

    def __init__(self, options=None):
        """Initialize base class."""
        if options is None:
            self.options = {}
        else:
            self.options = options

    def init(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the init() method '
                                  'yourself!')

    def run(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the run() method '
                                  'yourself!')

    def teardown(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the teardown() method '
                                  'yourself!')
