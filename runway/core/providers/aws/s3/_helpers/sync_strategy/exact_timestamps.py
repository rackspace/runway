"""Exact time stamps sync strategy.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/exacttimestamps.py

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, Optional

from typing_extensions import Literal

from .base import SizeAndLastModifiedSync

if TYPE_CHECKING:
    from ..file_generator import FileStats

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ExactTimestampsSync(SizeAndLastModifiedSync):
    """Exact time stamp."""

    NAME: ClassVar[Literal["exact_timestamps"]] = "exact_timestamps"

    def compare_time(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Compare modified time of two FileStats objects.

        Returns:
            True if the file does not need updating based on time of last
            modification and type of operation. False if the file does need
            updating based on the time of last modification and type of operation.

        """
        if not (src_file and dest_file):
            raise ValueError("src_file and dest_file must not be None")
        delta = dest_file.last_update - src_file.last_update
        if src_file.operation_name == "download":
            return delta.total_seconds() == 0
        return super().compare_time(src_file, dest_file)
