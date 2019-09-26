"""yamllint test runner."""
# filename contains underscore to prevent namespace collision
import glob
import logging
import os
from typing import Dict, Any, List  # pylint: disable=unused-import

from yamllint.cli import run as yamllint_run

from runway.tests.handlers.base import TestHandler
from runway.util import change_dir, ignore_exit_code_0

TYPE_NAME = 'yamllint'
LOGGER = logging.getLogger('runway')


class YamllintHandler(TestHandler):
    """Lints yaml."""

    @staticmethod
    def get_yaml_files_at_path(provided_path):
        # type: (str) -> List[str]
        """Return list of yaml files."""
        yaml_files = glob.glob(
            os.path.join(provided_path, '*.yaml')
        )
        yml_files = glob.glob(
            os.path.join(provided_path, '*.yml')
        )
        return yaml_files + yml_files

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Perform the actual test."""
        base_dir = os.getcwd()
        dirs_to_scan = cls.get_dirs(base_dir)

        if '.git' in dirs_to_scan:
            dirs_to_scan.remove('.git')  # not relevant for any repo operations

        if os.path.isfile(os.path.join(base_dir, '.yamllint')):
            yamllint_config = os.path.join(base_dir, '.yamllint')
        elif os.path.isfile(os.path.join(base_dir, '.yamllint.yml')):
            yamllint_config = os.path.join(base_dir, '.yamllint.yml')
        else:
            yamllint_config = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)
                ))),
                'templates',
                '.yamllint.yml'
            )

        with change_dir(base_dir):
            with ignore_exit_code_0():
                yamllint_run(
                    ["--config-file=%s" % yamllint_config] + dirs_to_scan +
                    cls.get_yaml_files_at_path(base_dir)
                )
