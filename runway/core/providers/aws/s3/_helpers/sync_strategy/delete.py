"""Delete sync strategy.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/delete.py

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import Literal

from .base import BaseSync

if TYPE_CHECKING:
    from ..file_generator import FileStats


LOGGER = logging.getLogger(__name__)


class DeleteSync(BaseSync):
    """Delete file."""

    NAME: ClassVar[Literal["delete"]] = "delete"

    def determine_should_sync(self, src_file: FileStats, dest_file: FileStats) -> bool:
        """Determine if file should sync."""
        dest_file.operation_name = "delete"
        LOGGER.debug(
            "syncing: (None) -> %s (remove), file does not "
            "exist at source (%s) and delete mode enabled",
            dest_file.src,
            dest_file.dest,
        )
        return True
