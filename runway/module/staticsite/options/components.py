"""Runway Static Site Module options component classes."""
from __future__ import annotations

from ...base import ModuleOptions
from .models import RunwayStaticSiteModuleOptionsDataModel


class StaticSiteOptions(ModuleOptions):
    """Static site options.

    Attributes:
        build_output: Directory where build output is placed. Defaults to current
            working directory.
        build_steps: List of commands to run to build the static site.
        data: Options parsed into a data model.
        extra_files: List of files that should be uploaded to S3 after the build.
            Used to dynamically create or select file.
        pre_build_steps: Commands to be run prior to the build process.
        source_hashing: Overrides for source hash calculation and tracking.

    """

    def __init__(self, data: RunwayStaticSiteModuleOptionsDataModel) -> None:
        """Instantiate class."""
        self.build_output = data.build_output
        self.build_steps = data.build_steps
        self.data = data
        self.extra_files = data.extra_files
        self.pre_build_steps = data.pre_build_steps
        self.source_hashing = data.source_hashing

    @classmethod
    def parse_obj(cls, obj: object) -> StaticSiteOptions:
        """Parse options definition and return an options object.

        Args:
            obj: Object to parse.

        """
        return cls(data=RunwayStaticSiteModuleOptionsDataModel.parse_obj(obj))
