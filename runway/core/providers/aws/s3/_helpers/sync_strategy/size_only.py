"""Size only strategy.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/sizeonly.py

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, Optional

from typing_extensions import Literal

from .base import BaseSync

if TYPE_CHECKING:
    from ..file_generator import FileStats


LOGGER = logging.getLogger(__name__.replace("._", "."))


class SizeOnlySync(BaseSync):
    """Only check size when determining if file should sync."""

    NAME: ClassVar[Literal["size_only"]] = "size_only"

    def determine_should_sync(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Determine if file should sync."""
        same_size = self.compare_size(src_file, dest_file)
        should_sync = not same_size
        if should_sync:
            LOGGER.debug(
                "syncing: %s -> %s, size_changed: %s",
                src_file.src if src_file else None,
                src_file.dest if src_file else None,
                not same_size,
            )
        return should_sync
