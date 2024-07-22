"""yamllint test runner."""

# filename contains underscore to prevent namespace collision
from __future__ import annotations

import glob
import logging
import os
import runpy
from typing import TYPE_CHECKING, Any

from ...tests.handlers.base import TestHandler
from ...utils import argv

if TYPE_CHECKING:
    from ...config.components.runway.base import ConfigProperty

TYPE_NAME = "yamllint"
LOGGER = logging.getLogger(__name__)


class YamllintHandler(TestHandler):
    """Lints yaml."""

    @staticmethod
    def get_yaml_files_at_path(provided_path: str) -> list[str]:
        """Return list of yaml files."""
        yaml_files = glob.glob(os.path.join(provided_path, "*.yaml"))  # noqa: PTH207, PTH118
        yml_files = glob.glob(os.path.join(provided_path, "*.yml"))  # noqa: PTH118, PTH207
        return yaml_files + yml_files

    @classmethod
    def get_yamllint_options(cls, path: str) -> list[str]:
        """Return yamllint option list."""
        yamllint_options: list[str] = []

        return yamllint_options + cls.get_dirs(path) + cls.get_yaml_files_at_path(path)

    @classmethod
    def handle(cls, name: str, args: ConfigProperty | dict[str, Any]) -> None:  # noqa: ARG003
        """Perform the actual test."""
        base_dir = os.getcwd()  # noqa: PTH109

        if os.path.isfile(os.path.join(base_dir, ".yamllint")):  # noqa: PTH118, PTH113
            yamllint_config = os.path.join(base_dir, ".yamllint")  # noqa: PTH118
        elif os.path.isfile(os.path.join(base_dir, ".yamllint.yml")):  # noqa: PTH113, PTH118
            yamllint_config = os.path.join(base_dir, ".yamllint.yml")  # noqa: PTH118
        else:
            yamllint_config = os.path.join(  # noqa: PTH118
                os.path.dirname(  # noqa: PTH120
                    os.path.dirname(  # noqa: PTH120
                        os.path.dirname(os.path.abspath(__file__))  # noqa: PTH120, PTH100
                    )
                ),
                "templates",
                ".yamllint.yml",
            )

        yamllint_options = [
            f"--config-file={yamllint_config}",
            *cls.get_yamllint_options(base_dir),
        ]

        with argv(*["yamllint", *yamllint_options]):
            runpy.run_module("yamllint", run_name="__main__")
