"""yamllint test runner."""
# filename contains underscore to prevent namespace collision
import glob
import logging
import os
import sys
import tempfile
from typing import Dict, Any, List  # pylint: disable=unused-import

from runway.tests.handlers.base import TestHandler
from runway.tests.handlers.script import ScriptHandler
from runway.util import change_dir

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
    def get_yamllint_options(cls, path, quote_paths=True):
        # type: (str, bool) -> List[str]
        """Return yamllint option list."""
        dirs_to_scan = cls.get_dirs(path)
        files_at_base = cls.get_yaml_files_at_path(path)
        yamllint_options = []

        if dirs_to_scan:
            yamllint_options.extend(
                ["\"%s\"" % x if quote_paths else x for x in dirs_to_scan]
            )
        if files_at_base:
            yamllint_options.extend(
                ["\"%s\"" % x if quote_paths else x for x in files_at_base]
            )

        return yamllint_options

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Perform the actual test."""
        base_dir = os.getcwd()

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

        yamllint_options = ["--config-file=%s" % yamllint_config]
        yamllint_options.extend(cls.get_yamllint_options(base_dir,
                                                         not getattr(sys, 'frozen', False)))

        if getattr(sys, 'frozen', False):
            # running in pyinstaller single-exe, so sys.executable will
            # be the all-in-one Runway binary

            # This would be a little more natural if yamllint was imported
            # directly, but that has unclear license implications so instead
            # we'll generate the setuptools invocation script here and shell
            # out to it
            yamllint_invocation_script = (
                "import sys;"
                "from yamllint.cli import run;"
                "sys.argv = [%s];"
                "sys.exit(run());" % ','.join(
                    "'%s'" % i for i in ['yamllint'] + yamllint_options
                )
            )

            temp_fd, temp_path = tempfile.mkstemp(prefix='yamllint')
            os.close(temp_fd)
            with open(temp_path, 'w') as fileobj:
                fileobj.write(yamllint_invocation_script)

            yl_cmd = sys.executable + ' run-python ' + temp_path
        else:
            # traditional python execution
            yl_cmd = "yamllint " + ' '.join(yamllint_options)
        with change_dir(base_dir):
            try:
                ScriptHandler().handle(
                    'yamllint',
                    {'commands': [yl_cmd]}
                )
            finally:
                if getattr(sys, 'frozen', False):
                    os.remove(temp_path)
