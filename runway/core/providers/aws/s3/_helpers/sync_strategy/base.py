"""Base sync strategies.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/base.py

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, List, Optional

from typing_extensions import Literal

if TYPE_CHECKING:
    from botocore.session import Session

    from ..file_generator import FileStats
    from ..parameters import ParametersDataModel


LOGGER = logging.getLogger(__name__.replace("._", "."))

ValidSyncType = Literal["file_at_src_and_dest", "file_not_at_dest", "file_not_at_src"]
VALID_SYNC_TYPES: List[ValidSyncType] = [
    "file_at_src_and_dest",
    "file_not_at_dest",
    "file_not_at_src",
]


class BaseSync:
    """Base sync strategy.

    To create a new sync strategy, subclass from this class.

    """

    NAME: ClassVar[Optional[str]] = None

    sync_type: ValidSyncType

    def __init__(self, sync_type: ValidSyncType = "file_at_src_and_dest") -> None:
        """Instantiate class.

        Args:
            sync_type: This determines where the sync strategy will be
                used. There are three strings to choose from.

        """
        self._check_sync_type(sync_type)
        self.sync_type = sync_type

    @property
    def name(self) -> Optional[str]:
        """Retrieve the ``name`` of the sync strategy's ``ARGUMENT``."""
        return self.NAME

    @staticmethod
    def _check_sync_type(sync_type: str) -> None:
        if sync_type not in VALID_SYNC_TYPES:
            raise ValueError(
                f"Unknown sync_type: {sync_type}.\nValid options are {VALID_SYNC_TYPES}."
            )

    def register_strategy(self, session: Session) -> None:
        """Register the sync strategy class to the given session."""
        session.register("choosing-s3-sync-strategy", self.use_sync_strategy)

    def determine_should_sync(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Determine if file should sync.

        This function takes two ``FileStat`` objects (one from the source and
        one from the destination). Then makes a decision on whether a given
        operation (e.g. a upload, copy, download) should be allowed
        to take place.

        The function currently raises a ``NotImplementedError``. So this
        method must be overwritten when this class is subclassed. Note
        that this method must return a Boolean as documented below.

        Args:
            src_file: A representation of the operation that is to be
                performed on a specific file existing in the source. Note if
                the file does not exist at the source, ``src_file`` is None.
            dest_file: A representation of the operation that is to be
                performed on a specific file existing in the destination. Note if
                the file does not exist at the destination, ``dest_file`` is None.

        Return:
            True if an operation based on the ``FileStat`` should be allowed to occur.
            False if if an operation based on the ``FileStat`` should not be
            allowed to occur. Note the operation being referred to depends on
            the ``sync_type`` of the sync strategy:

            'file_at_src_and_dest': refers to ``src_file``

            'file_not_at_dest': refers to ``src_file``

            'file_not_at_src': refers to ``dest_file``

        """
        raise NotImplementedError("determine_should_sync")

    def use_sync_strategy(self, params: ParametersDataModel, **_) -> Optional[BaseSync]:
        """Determine which sync strategy to use.

        The sync strategy object must be returned by this method
        if it is to be chosen as the sync strategy to use.

        Args:
            params: All arguments that a sync strategy is able to process.

        """
        if self.name:
            if params.get(self.name):
                # Return the sync strategy object to be used for syncing.
                return self
        return None

    @staticmethod
    def compare_size(
        src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Compare the size of two FileStats objects."""
        if not (src_file and dest_file):
            raise ValueError("src_file and dest_file must not be None")
        return src_file.size == dest_file.size

    # pylint: disable=no-self-use
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
        cmd = src_file.operation_name
        if cmd in ["copy", "upload"]:
            if delta.total_seconds() >= 0:
                # Destination is newer than source.
                return True
            return False
        if cmd == "download":
            if delta.total_seconds() <= 0:
                return True
        return False


class MissingFileSync(BaseSync):
    """File is missing from destination."""

    def __init__(
        self, sync_type: Literal["file_not_at_dest"] = "file_not_at_dest"
    ) -> None:
        """Instantiate class.

        Args:
            sync_type: This determines where the sync strategy will be
                used. There are three strings to choose from.

        """
        super().__init__(sync_type)

    def determine_should_sync(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Determine if file should sync."""
        LOGGER.debug(
            "syncing: %s -> %s, file does not exist at destination",
            src_file.src if src_file else None,
            src_file.dest if src_file else None,
        )
        return True


class NeverSync(BaseSync):
    """Never sync file."""

    def __init__(
        self, sync_type: Literal["file_not_at_src"] = "file_not_at_src"
    ) -> None:
        """Instantiate class.

        Args:
            sync_type: This determines where the sync strategy will be
                used. There are three strings to choose from.

        """
        super().__init__(sync_type)

    def determine_should_sync(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Determine if file should sync."""
        return False


class SizeAndLastModifiedSync(BaseSync):
    """Sync based on size and last modified date."""

    def determine_should_sync(
        self, src_file: Optional[FileStats], dest_file: Optional[FileStats]
    ) -> bool:
        """Determine if file should sync."""
        same_size = self.compare_size(src_file, dest_file)
        same_last_modified_time = self.compare_time(src_file, dest_file)
        should_sync = (not same_size) or (not same_last_modified_time)
        if should_sync:
            LOGGER.debug(
                "syncing: %s -> %s, size: %s -> %s, modified time: %s -> %s",
                src_file.src if src_file else None,
                src_file.dest if src_file else None,
                src_file.size if src_file else None,
                dest_file.size if dest_file else None,
                src_file.last_update if src_file else None,
                dest_file.last_update if dest_file else None,
            )
        return should_sync
