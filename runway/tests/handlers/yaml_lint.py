"""yamllint test runner."""
# filename contains underscore to prevent namespace collision
from __future__ import annotations

import glob
import logging
import os
import runpy
from typing import TYPE_CHECKING, Any, Dict, List, Union

from ...tests.handlers.base import TestHandler
from ...utils import argv

if TYPE_CHECKING:
    from ...config.components.runway.base import ConfigProperty

TYPE_NAME = "yamllint"
LOGGER = logging.getLogger(__name__)


class YamllintHandler(TestHandler):
    """Lints yaml."""

    @staticmethod
    def get_yaml_files_at_path(provided_path: str) -> List[str]:
        """Return list of yaml files."""
        yaml_files = glob.glob(os.path.join(provided_path, "*.yaml"))
        yml_files = glob.glob(os.path.join(provided_path, "*.yml"))
        return yaml_files + yml_files

    @classmethod
    def get_yamllint_options(cls, path: str) -> List[str]:
        """Return yamllint option list."""
        yamllint_options: List[str] = []

        return yamllint_options + cls.get_dirs(path) + cls.get_yaml_files_at_path(path)

    @classmethod
    def handle(cls, name: str, args: Union[ConfigProperty, Dict[str, Any]]) -> None:
        """Perform the actual test."""
        base_dir = os.getcwd()

        if os.path.isfile(os.path.join(base_dir, ".yamllint")):
            yamllint_config = os.path.join(base_dir, ".yamllint")
        elif os.path.isfile(os.path.join(base_dir, ".yamllint.yml")):
            yamllint_config = os.path.join(base_dir, ".yamllint.yml")
        else:
            yamllint_config = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "templates",
                ".yamllint.yml",
            )

        yamllint_options = [
            f"--config-file={yamllint_config}",
            *cls.get_yamllint_options(base_dir),
        ]

        with argv(*["yamllint"] + yamllint_options):
            runpy.run_module("yamllint", run_name="__main__")
